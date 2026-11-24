import json
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from gestor_inventario.models import ConsumoPersonal, Proveedor
from productos.models import Producto, Transaccion
from salidas.models import MotivoSalida, SalidaProducto

from .forms import PesosField
from .models import CajaDiaria, Cobro, CobroItem, PagoProveedor


def a_la_hora(fecha, hora, minuto=0):
    """Fecha y hora en la zona de la tienda (Bogotá)."""
    return timezone.make_aware(datetime.combine(fecha, time(hora, minuto)))


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_superuser('admin', 'a@a.co', 'clave-segura-123', first_name='Nicolás', last_name='Rojas')
        cls.normal = User.objects.create_user('normal', 'n@a.co', 'clave-segura-123')
        cls.producto = Producto.objects.create(nombre='Gaseosa', precio_unitario=3000, cantidad=1, existencias=100, unidad_medida='Mililitros')
        cls.proveedor = Proveedor.objects.create(nombre_empresa='Postobón', nit='900', contacto_nombre='Ana', telefono='1', email='p@p.co')
        cls.inactivo = Proveedor.objects.create(nombre_empresa='Viejo', nit='901', activo=False)
        cls.con_cambio = MotivoSalida.objects.create(nombre='Vencido', da_cambio=True)
        cls.sin_cambio = MotivoSalida.objects.create(nombre='Perdido', da_cambio=False)

    def setUp(self):
        self.client.force_login(self.admin)
        self.hoy = timezone.localdate()

    def vender(self, cantidad, precio=3000, cuando=None):
        datos = dict(nom_producto='Gaseosa', cantidad=cantidad, precio=precio)
        if cuando:
            datos['fecha_hora'] = cuando
        return Transaccion.objects.create(**datos)

    def abrir(self, base='50.000'):
        return self.client.post(reverse('abrir_caja'), {'base_inicial': base})

    def caja_hoy(self):
        return CajaDiaria.objects.get(fecha=self.hoy)

    def cerrar(self, caja, contado, transferencias='0', observacion='', confirmado=True, esperado=None):
        datos = {'contado': contado, 'transferencias': transferencias, 'observacion': observacion}
        if confirmado:
            datos['confirmado'] = '1'
            datos['esperado_visto'] = str(esperado)
        return self.client.post(reverse('cerrar_caja', args=[caja.id]), datos)


class PermisosTests(Base):
    def test_anonimo_va_al_login(self):
        self.client.logout()
        for url in (reverse('caja_hoy'), reverse('historial_cajas')):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302)
            self.assertIn(reverse('login'), r['Location'])

    def test_usuario_normal_no_entra(self):
        self.client.force_login(self.normal)
        r = self.client.get(reverse('caja_hoy'))
        self.assertRedirects(r, reverse('lista_productos'), fetch_redirect_response=False)
        r = self.client.post(reverse('abrir_caja'), {'base_inicial': '1000'})
        self.assertFalse(CajaDiaria.objects.exists())

    def test_acciones_solo_por_post(self):
        self.assertEqual(self.client.get(reverse('abrir_caja')).status_code, 405)
        self.abrir()
        caja = self.caja_hoy()
        self.assertEqual(self.client.get(reverse('registrar_pago', args=[caja.id])).status_code, 405)


class AperturaTests(Base):
    def test_pagina_sin_abrir(self):
        r = self.client.get(reverse('caja_hoy'))
        self.assertContains(r, 'Abre la caja')
        self.assertContains(r, 'name="base_inicial"')

    def test_abrir_con_puntos_de_miles(self):
        r = self.abrir('$ 150.000')
        self.assertRedirects(r, reverse('caja_hoy'))
        caja = self.caja_hoy()
        self.assertEqual(caja.base_inicial, 150000)
        self.assertEqual(caja.abierta_por, self.admin)
        self.assertEqual(caja.abierta_por_nombre, 'Nicolás Rojas')
        self.assertTrue(caja.esta_abierta)

    def test_abrir_con_cero(self):
        self.abrir('0')
        self.assertEqual(self.caja_hoy().base_inicial, 0)

    def test_valores_invalidos(self):
        for malo in ('-500', '50000,5', '12.34', 'abc', '', '5.00.0', '99999999999'):
            r = self.abrir(malo)
            self.assertEqual(r.status_code, 200, malo)
            self.assertContains(r, 'cj-err')
        self.assertFalse(CajaDiaria.objects.exists())

    def test_solo_una_caja_por_dia(self):
        self.abrir('1000')
        r = self.abrir('2000')
        self.assertRedirects(r, reverse('caja_hoy'))
        self.assertEqual(CajaDiaria.objects.count(), 1)
        self.assertEqual(self.caja_hoy().base_inicial, 1000)

    def test_no_abre_si_quedo_una_abierta_de_antes(self):
        CajaDiaria.objects.create(fecha=self.hoy - timedelta(days=2), base_inicial=0)
        r = self.client.get(reverse('caja_hoy'))
        self.assertContains(r, 'quedó abierta')
        self.abrir('1000')
        self.assertFalse(CajaDiaria.objects.filter(fecha=self.hoy).exists())

    def test_avisa_ventas_de_hoy_antes_de_abrir(self):
        self.vender(2)
        r = self.client.get(reverse('caja_hoy'))
        self.assertContains(r, '1 venta</strong>')


class PagosTests(Base):
    def setUp(self):
        super().setUp()
        self.abrir('100.000')
        self.caja = self.caja_hoy()
        self.url = reverse('registrar_pago', args=[self.caja.id])

    def test_pago_a_proveedor_registrado(self):
        r = self.client.post(self.url, {'proveedor': self.proveedor.id, 'valor': '40.000', 'concepto': 'Pedido'})
        self.assertRedirects(r, reverse('caja_hoy'))
        pago = PagoProveedor.objects.get()
        self.assertEqual((pago.proveedor, pago.proveedor_nombre, pago.valor), (self.proveedor, 'Postobón', 40000))

    def test_pago_a_otro(self):
        self.client.post(self.url, {'proveedor': 'otro', 'otro_nombre': 'Don Pepe', 'valor': '5000'})
        pago = PagoProveedor.objects.get()
        self.assertIsNone(pago.proveedor)
        self.assertEqual(pago.proveedor_nombre, 'Don Pepe')

    def test_errores_del_pago(self):
        casos = [
            {'proveedor': '', 'valor': '1000'},
            {'proveedor': 'otro', 'otro_nombre': '', 'valor': '1000'},
            {'proveedor': self.inactivo.id, 'valor': '1000'},
            {'proveedor': '99999', 'valor': '1000'},
            {'proveedor': 'x1', 'valor': '1000'},
            {'proveedor': self.proveedor.id, 'valor': '0'},
            {'proveedor': self.proveedor.id, 'valor': ''},
            {'proveedor': self.proveedor.id, 'valor': '100.001'},   # más de lo que hay en la caja
        ]
        for datos in casos:
            r = self.client.post(self.url, datos)
            self.assertEqual(r.status_code, 200, datos)
            self.assertContains(r, 'cj-err')
        self.assertFalse(PagoProveedor.objects.exists())

    def test_el_tope_cuenta_las_ventas(self):
        self.vender(10)   # $30.000 más en la caja
        r = self.client.post(self.url, {'proveedor': self.proveedor.id, 'valor': '130.000'})
        self.assertRedirects(r, reverse('caja_hoy'))

    def test_textos_raros_se_muestran_escapados(self):
        malo = '<script>alert(1)</script>'
        self.client.post(self.url, {'proveedor': 'otro', 'otro_nombre': malo, 'concepto': '<img src=x onerror=alert(1)>', 'valor': '1000'})
        r = self.client.get(reverse('caja_hoy'))
        self.assertNotContains(r, malo)
        self.assertNotContains(r, '<img src=x')
        self.assertContains(r, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.cerrar(self.caja, '99.000', observacion=malo, esperado=99000)
        r = self.client.get(reverse('detalle_caja', args=[self.caja.id]))
        self.assertNotContains(r, malo)

    def test_quitar_pago_con_caja_abierta(self):
        self.client.post(self.url, {'proveedor': self.proveedor.id, 'valor': '1000'})
        pago = PagoProveedor.objects.get()
        self.client.post(reverse('eliminar_pago', args=[pago.id]))
        self.assertFalse(PagoProveedor.objects.exists())

    def test_con_caja_cerrada_no_hay_pagos(self):
        self.client.post(self.url, {'proveedor': self.proveedor.id, 'valor': '1000'})
        pago = PagoProveedor.objects.get()
        self.cerrar(self.caja, '99.000', esperado=99000)
        self.client.post(self.url, {'proveedor': self.proveedor.id, 'valor': '500'})
        self.client.post(reverse('eliminar_pago', args=[pago.id]))
        self.assertEqual(PagoProveedor.objects.count(), 1)
        with self.assertRaises(ValidationError):
            pago.delete()


class CierreTests(Base):
    def preparar_dia(self):
        """Un día completo con un poco de todo."""
        self.abrir('50.000')
        self.caja = self.caja_hoy()
        self.vender(3)                     # 9.000
        self.vender(2, precio=5000)        # 10.000
        ConsumoPersonal.objects.create(persona='Carlos', total=4000)
        ConsumoPersonal.objects.create(persona='Sara', total=999, activo=False)   # borrado: no cuenta
        ConsumoPersonal.objects.create(persona='Sara', total=1000, fecha=self.hoy - timedelta(days=1))   # otro día
        SalidaProducto.objects.create(producto=self.producto, nom_producto='Gaseosa', precio_unitario=3000, cantidad=2, motivo=self.sin_cambio, descripcion='x')
        SalidaProducto.objects.create(producto=self.producto, nom_producto='Gaseosa', precio_unitario=3000, cantidad=1, motivo=self.con_cambio, descripcion='x')
        self.client.post(reverse('registrar_pago', args=[self.caja.id]), {'proveedor': self.proveedor.id, 'valor': '7.000'})
        # esperado sin transferencias = 50.000 + 19.000 - 7.000 = 62.000

    def test_resumen_en_la_pagina_de_cierre(self):
        self.preparar_dia()
        r = self.client.get(reverse('cerrar_caja', args=[self.caja.id]))
        self.assertEqual(r.context['r']['ventas_total'], 19000)
        self.assertEqual(r.context['r']['ventas_cantidad'], 2)
        self.assertEqual(r.context['r']['ventas_unidades'], 5)
        self.assertEqual(r.context['r']['consumos_total'], 4000)
        self.assertEqual(r.context['r']['salidas_perdida_total'], 6000)
        self.assertEqual(r.context['r']['salidas_cambio_total'], 3000)
        self.assertEqual(r.context['r']['pagos_proveedor_total'], 7000)
        self.assertEqual(r.context['r']['esperado_sin_transferencias'], 62000)

    def test_primero_pide_confirmar(self):
        self.preparar_dia()
        r = self.cerrar(self.caja, '62.000', confirmado=False)
        self.assertContains(r, 'Sí, cerrar la caja')
        self.assertContains(r, 'Cuadra')
        self.assertTrue(CajaDiaria.objects.get(pk=self.caja.pk).esta_abierta)

    def test_cerrar_cuadra_y_guarda_la_foto(self):
        self.preparar_dia()
        r = self.cerrar(self.caja, '62.000', esperado=62000)
        self.assertRedirects(r, reverse('detalle_caja', args=[self.caja.id]))
        c = CajaDiaria.objects.get(pk=self.caja.pk)
        self.assertEqual(c.estado, CajaDiaria.CERRADA)
        self.assertEqual((c.ventas_total, c.ventas_cantidad, c.ventas_unidades), (19000, 2, 5))
        self.assertEqual((c.consumos_total, c.consumos_cantidad), (4000, 1))
        self.assertEqual((c.salidas_perdida_total, c.salidas_perdida_unidades, c.salidas_cambio_total, c.salidas_cantidad), (6000, 2, 3000, 2))
        self.assertEqual((c.pagos_proveedor_total, c.pagos_proveedor_cantidad), (7000, 1))
        self.assertEqual((c.esperado, c.contado, c.diferencia, c.resultado), (62000, 62000, 0, CajaDiaria.CUADRA))
        self.assertEqual(c.cerrada_por, self.admin)
        self.assertIsNotNone(c.cerrada_en)

    def test_transferencias_bajan_lo_esperado(self):
        self.preparar_dia()
        self.cerrar(self.caja, '52.000', transferencias='10.000', esperado=52000)
        c = CajaDiaria.objects.get(pk=self.caja.pk)
        self.assertEqual((c.transferencias, c.esperado, c.diferencia), (10000, 52000, 0))

    def test_transferencias_no_pueden_pasar_lo_vendido(self):
        self.preparar_dia()
        r = self.cerrar(self.caja, '0', transferencias='19.001', confirmado=False)
        self.assertContains(r, 'No puede ser más de lo vendido')

    def test_faltante_exige_observacion(self):
        self.preparar_dia()
        r = self.cerrar(self.caja, '60.000', confirmado=False)
        self.assertContains(r, 'Hay sobrante o faltante')
        r = self.cerrar(self.caja, '60.000', observacion='Se dio mal un vuelto', esperado=62000)
        c = CajaDiaria.objects.get(pk=self.caja.pk)
        self.assertEqual((c.diferencia, c.resultado, c.observacion), (-2000, CajaDiaria.FALTANTE, 'Se dio mal un vuelto'))

    def test_sobrante(self):
        self.preparar_dia()
        self.cerrar(self.caja, '63.500', observacion='Sobró del día', esperado=62000)
        c = CajaDiaria.objects.get(pk=self.caja.pk)
        self.assertEqual((c.diferencia, c.resultado), (1500, CajaDiaria.SOBRANTE))

    def test_si_entra_una_venta_mientras_revisa(self):
        self.preparar_dia()
        self.vender(1)   # llegó una venta de 3.000 después de ver el paso de confirmar
        r = self.cerrar(self.caja, '62.000', esperado=62000)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Mientras revisabas')
        self.assertTrue(CajaDiaria.objects.get(pk=self.caja.pk).esta_abierta)

    def test_venta_nueva_con_observacion_vuelve_a_confirmar(self):
        self.preparar_dia()
        self.vender(1)
        r = self.cerrar(self.caja, '62.000', observacion='Faltó plata del vuelto', esperado=62000)
        self.assertContains(r, 'Mientras revisabas')
        self.assertEqual(r.context['paso'], 'confirmar')
        self.assertEqual(r.context['datos']['esperado'], 65000)
        self.assertTrue(CajaDiaria.objects.get(pk=self.caja.pk).esta_abierta)
        # Al confirmar con lo nuevo, ya cierra
        self.cerrar(self.caja, '62.000', observacion='Faltó plata del vuelto', esperado=65000)
        self.assertEqual(CajaDiaria.objects.get(pk=self.caja.pk).diferencia, -3000)

    def test_sin_ventas_se_cierra_en_cero(self):
        self.abrir('0')
        caja = self.caja_hoy()
        self.cerrar(caja, '0', esperado=0)
        c = CajaDiaria.objects.get(pk=caja.pk)
        self.assertEqual((c.estado, c.ventas_total, c.diferencia, c.resultado), (CajaDiaria.CERRADA, 0, 0, CajaDiaria.CUADRA))

    def test_no_se_cierra_dos_veces(self):
        self.preparar_dia()
        self.cerrar(self.caja, '62.000', esperado=62000)
        r = self.cerrar(self.caja, '1', observacion='otra vez', esperado=62000)
        self.assertRedirects(r, reverse('detalle_caja', args=[self.caja.id]))
        self.assertEqual(CajaDiaria.objects.get(pk=self.caja.pk).contado, 62000)

    def test_cerrada_no_se_edita_ni_se_borra(self):
        self.preparar_dia()
        self.cerrar(self.caja, '62.000', esperado=62000)
        c = CajaDiaria.objects.get(pk=self.caja.pk)
        c.contado = 1
        with self.assertRaises(ValidationError):
            c.save()
        with self.assertRaises(ValidationError):
            c.delete()
        with self.assertRaises(ValidationError):
            CajaDiaria.objects.filter(pk=c.pk).update(contado=1)
        with self.assertRaises(ValidationError):
            CajaDiaria.objects.all().delete()

    def test_ventas_despues_del_cierre(self):
        self.preparar_dia()
        self.cerrar(self.caja, '62.000', esperado=62000)
        self.vender(4)
        r = self.client.get(reverse('detalle_caja', args=[self.caja.id]))
        self.assertContains(r, 'después del cierre')
        self.assertEqual(r.context['despues']['ventas'], 1)
        # El cierre guardado no cambia
        self.assertEqual(CajaDiaria.objects.get(pk=self.caja.pk).ventas_total, 19000)
        r = self.client.get(reverse('caja_hoy'))
        self.assertContains(r, 'No están en este cierre')

    def test_cerrar_una_caja_pendiente_de_otro_dia(self):
        ayer = self.hoy - timedelta(days=1)
        caja = CajaDiaria.objects.create(fecha=ayer, base_inicial=10000)
        self.vender(1, cuando=a_la_hora(ayer, 15))
        self.vender(5)   # hoy: no entra en la de ayer
        r = self.client.get(reverse('cerrar_caja', args=[caja.id]))
        self.assertEqual(r.context['r']['ventas_total'], 3000)
        self.cerrar(caja, '13.000', esperado=13000)
        self.assertFalse(CajaDiaria.objects.get(pk=caja.pk).esta_abierta)
        self.abrir('0')
        self.assertTrue(CajaDiaria.objects.filter(fecha=self.hoy).exists())

    def test_corregir_vuelve_al_formulario(self):
        self.preparar_dia()
        r = self.client.post(reverse('cerrar_caja', args=[self.caja.id]), {'contado': '60000', 'transferencias': '0', 'observacion': 'hola mundo', 'corregir': '1'})
        self.assertContains(r, 'Revisar cierre')
        self.assertContains(r, 'value="60000"')


class HistorialTests(Base):
    def crear_cerrada(self, dias_atras, ventas, contado, resultado, observacion=''):
        caja = CajaDiaria.objects.create(fecha=self.hoy - timedelta(days=dias_atras), base_inicial=0)
        CajaDiaria.objects.filter(pk=caja.pk).update(
            estado=CajaDiaria.CERRADA, observacion=observacion, ventas_total=ventas, esperado=ventas, contado=contado,
            diferencia=contado - ventas, resultado=resultado, cerrada_en=timezone.now(), cerrada_por_nombre='Nico',
            salidas_perdida_total=100, consumos_total=50, pagos_proveedor_total=10,
        )
        return caja

    def setUp(self):
        super().setUp()
        self.a = self.crear_cerrada(1, 1000, 1000, CajaDiaria.CUADRA)
        self.b = self.crear_cerrada(2, 2000, 2500, CajaDiaria.SOBRANTE, observacion='=HYPERLINK("x")')
        self.c = self.crear_cerrada(40, 3000, 2000, CajaDiaria.FALTANTE)
        CajaDiaria.objects.create(fecha=self.hoy, base_inicial=0)   # abierta: no sale en el historial

    def test_lista_mas_reciente_primero(self):
        r = self.client.get(reverse('historial_cajas'))
        self.assertEqual(list(r.context['cajas']), [self.a, self.b, self.c])
        self.assertEqual(r.context['suma']['vendido'], 6000)
        self.assertEqual(r.context['suma']['diferencias'], -500)
        self.assertEqual(r.context['suma']['perdidas'], 300)

    def test_filtro_por_resultado(self):
        r = self.client.get(reverse('historial_cajas'), {'resultado': 'faltante'})
        self.assertEqual(list(r.context['cajas']), [self.c])
        # El resumen sigue siendo de todo el período
        self.assertEqual(r.context['suma']['dias'], 3)

    def test_filtro_por_mes(self):
        mes = f'{self.c.fecha:%Y-%m}'
        r = self.client.get(reverse('historial_cajas'), {'mes': mes})
        self.assertIn(self.c, r.context['cajas'])
        self.assertTrue(all(f'{x.fecha:%Y-%m}' == mes for x in r.context['cajas']))

    def test_parametros_raros_no_rompen(self):
        for params in ({'mes': '2026-99'}, {'mes': '<script>'}, {'resultado': 'x'}, {'por': '999'}, {'pagina': 'abc'}, {'pagina': '-1'}):
            r = self.client.get(reverse('historial_cajas'), params)
            self.assertEqual(r.status_code, 200, params)

    def test_paginacion(self):
        for i in range(3, 25):
            self.crear_cerrada(i + 50, 10, 10, CajaDiaria.CUADRA)
        r = self.client.get(reverse('historial_cajas'), {'por': '20'})
        self.assertEqual(len(r.context['cajas']), 20)
        r = self.client.get(reverse('historial_cajas'), {'por': '20', 'pagina': '2'})
        self.assertEqual(len(r.context['cajas']), 5)

    def test_csv(self):
        r = self.client.get(reverse('historial_cajas'), {'formato': 'csv'})
        self.assertEqual(r['Content-Type'], 'text/csv; charset=utf-8')
        texto = r.content.decode('utf-8-sig')
        self.assertEqual(len(texto.strip().splitlines()), 4)   # encabezado + 3 cierres
        self.assertIn("'=HYPERLINK", texto)

    def test_detalle_y_caja_abierta(self):
        r = self.client.get(reverse('detalle_caja', args=[self.b.id]))
        self.assertContains(r, 'Sobraron $500')
        abierta = CajaDiaria.objects.get(fecha=self.hoy)
        r = self.client.get(reverse('detalle_caja', args=[abierta.id]))
        self.assertRedirects(r, reverse('caja_hoy'))
        self.assertEqual(self.client.get(reverse('detalle_caja', args=[99999])).status_code, 404)


class PesosFieldTests(TestCase):
    def test_lo_que_acepta(self):
        campo = PesosField()
        for texto, valor in (('50000', 50000), ('50.000', 50000), ('$ 1.250.000', 1250000), (' 0 ', 0)):
            self.assertEqual(campo.clean(texto), valor)

    def test_lo_que_no(self):
        campo = PesosField()
        for texto in ('-1', '1,5', '1.5', 'diez', '1.0000', '1000000000'):
            with self.assertRaises(ValidationError, msg=texto):
                campo.clean(texto)


class CobroTests(Base):
    """El carrito de la lista de productos: un cobro con varias ventas y cómo se pagó."""

    def setUp(self):
        super().setUp()
        self.producto.refresh_from_db()
        self.pan = Producto.objects.create(nombre='Pan', precio_unitario=6500, cantidad=1, existencias=5, unidad_medida='Gramos')

    def cobrar(self, items, metodo='efectivo', **extra):
        datos = {'items': items, 'metodo': metodo, **extra}
        return self.client.post(reverse('cobrar_carrito'), data=json.dumps(datos), content_type='application/json')

    def carrito(self, gaseosas=2, panes=1):
        return [{'id': self.producto.id, 'cantidad': gaseosas}, {'id': self.pan.id, 'cantidad': panes}]

    def test_efectivo_con_vuelto(self):
        r = self.cobrar(self.carrito(), recibido='20.000')
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        self.assertTrue(d['ok'])
        self.assertEqual(d['cobro'], {'id': d['cobro']['id'], 'total': 12500, 'efectivo': 12500, 'transferencia': 0, 'vuelto': 7500})
        self.assertIn('Vuelto: $7.500', d['mensaje'])
        self.assertEqual(d['existencias'], {str(self.producto.id): 98, str(self.pan.id): 4})
        cobro = Cobro.objects.get()
        self.assertEqual((cobro.metodo, cobro.recibido, cobro.registrado_por), ('efectivo', 20000, self.admin))
        ventas = Transaccion.objects.order_by('nom_producto')
        self.assertEqual([(v.nom_producto, v.cantidad, int(v.total)) for v in ventas], [('Gaseosa', 2, 6000), ('Pan', 1, 6500)])
        self.assertEqual(CobroItem.objects.filter(cobro=cobro).count(), 2)

    def test_efectivo_justo_sin_recibido(self):
        r = self.cobrar(self.carrito())
        self.assertEqual(r.json()['cobro']['vuelto'], 0)
        self.assertIsNone(Cobro.objects.get().recibido)

    def test_transferencia(self):
        r = self.cobrar(self.carrito(), 'transferencia', recibido='50000')
        c = Cobro.objects.get()
        self.assertEqual((c.efectivo, c.transferencia, c.vuelto, c.recibido), (0, 12500, 0, None))
        self.assertIn('por transferencia', r.json()['mensaje'])

    def test_mixto(self):
        r = self.cobrar(self.carrito(), 'mixto', efectivo='5.000')
        self.assertEqual(r.status_code, 200)
        c = Cobro.objects.get()
        self.assertEqual((c.metodo, c.efectivo, c.transferencia), ('mixto', 5000, 7500))

    def test_mixto_con_vuelto_del_efectivo(self):
        self.cobrar(self.carrito(), 'mixto', efectivo=5000, recibido=10000)
        self.assertEqual(Cobro.objects.get().vuelto, 5000)

    def test_pagos_que_no_sirven(self):
        casos = [
            ('mixto', {'efectivo': '0'}), ('mixto', {'efectivo': '12500'}), ('mixto', {'efectivo': '20000'}),
            ('mixto', {}), ('mixto', {'efectivo': 'abc'}), ('mixto', {'efectivo': 3000, 'recibido': 2000}),
            ('efectivo', {'recibido': '12.499'}), ('tarjeta', {}), (None, {}),
        ]
        for metodo, extra in casos:
            r = self.cobrar(self.carrito(), metodo, **extra)
            self.assertEqual(r.status_code, 400, (metodo, extra))
            self.assertFalse(r.json()['ok'])
        self.assertFalse(Cobro.objects.exists())
        self.assertFalse(Transaccion.objects.exists())

    def test_si_un_producto_no_alcanza_no_se_vende_nada(self):
        r = self.cobrar(self.carrito(gaseosas=3, panes=6))
        self.assertEqual(r.status_code, 400)
        self.assertIn('Pan (quedan 5)', r.json()['mensaje'])
        self.assertEqual(r.json()['existencias'][str(self.pan.id)], 5)
        self.producto.refresh_from_db(); self.pan.refresh_from_db()
        self.assertEqual((self.producto.existencias, self.pan.existencias), (100, 5))
        self.assertFalse(Transaccion.objects.exists())

    def test_productos_repetidos_se_suman(self):
        self.cobrar([{'id': self.pan.id, 'cantidad': 1}, {'id': self.pan.id, 'cantidad': 2}])
        venta = Transaccion.objects.get()
        self.assertEqual((venta.cantidad, int(venta.total)), (3, 19500))

    def test_el_precio_lo_pone_el_servidor(self):
        self.cobrar([{'id': self.pan.id, 'cantidad': 1, 'precio': 1, 'total': 1}], total=1)
        self.assertEqual(Cobro.objects.get().total, 6500)

    def test_carritos_mal_armados(self):
        malos = [
            [], None, 'x', [{'id': self.pan.id, 'cantidad': 0}], [{'id': self.pan.id, 'cantidad': -1}],
            [{'id': self.pan.id, 'cantidad': 'dos'}], [{'id': self.pan.id, 'cantidad': 1.5}], [{'id': 999999, 'cantidad': 1}],
            [{'cantidad': 1}], ['hola'], [{'id': True, 'cantidad': 1}],
        ]
        for items in malos:
            r = self.cobrar(items)
            self.assertEqual(r.status_code, 400, items)
        r = self.client.post(reverse('cobrar_carrito'), data='no es json', content_type='application/json')
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Transaccion.objects.exists())

    def test_permisos(self):
        self.assertEqual(self.client.get(reverse('cobrar_carrito')).status_code, 405)
        self.client.force_login(self.normal)
        r = self.cobrar(self.carrito())
        self.assertEqual(r.status_code, 302)
        self.client.logout()
        self.cobrar(self.carrito())
        self.assertFalse(Transaccion.objects.exists())

    def test_cobro_no_se_cambia_ni_se_borra(self):
        self.cobrar(self.carrito())
        c = Cobro.objects.get()
        c.total = 1
        with self.assertRaises(ValidationError):
            c.save()
        with self.assertRaises(ValidationError):
            c.delete()
        with self.assertRaises(ValidationError):
            Cobro.objects.update(total=1)
        with self.assertRaises(ValidationError):
            Cobro.objects.all().delete()

    def test_avisa_si_la_caja_no_esta_abierta(self):
        r = self.cobrar(self.carrito())
        self.assertIn('no está abierta', r.json()['mensaje'])
        self.abrir('0')
        r = self.cobrar(self.carrito())
        self.assertNotIn('no está abierta', r.json()['mensaje'])


class CajaConCobrosTests(Base):
    """La caja usa lo que se cobró con el carrito: ya sabe qué fue efectivo y qué transferencia."""

    def setUp(self):
        super().setUp()
        self.pan = Producto.objects.create(nombre='Pan', precio_unitario=6500, cantidad=1, existencias=50, unidad_medida='Gramos')
        self.abrir('50.000')
        self.caja = self.caja_hoy()

    def cobrar(self, items, metodo='efectivo', **extra):
        return self.client.post(reverse('cobrar_carrito'), data=json.dumps({'items': items, 'metodo': metodo, **extra}),
                                content_type='application/json')

    def dia_mezclado(self):
        self.cobrar([{'id': self.producto.id, 'cantidad': 3}])                            # 9.000 efectivo
        self.cobrar([{'id': self.pan.id, 'cantidad': 1}], 'transferencia')                # 6.500 transferencia
        self.cobrar([{'id': self.producto.id, 'cantidad': 2}], 'mixto', efectivo=1000)   # 1.000 + 5.000
        self.vender(1)                                                                    # 3.000 sin cobro
        # ventas 24.500 · transferencias del carrito 11.500 · debería haber 50.000 + 24.500 - 11.500 = 63.000

    def test_resumen_con_cobros(self):
        self.dia_mezclado()
        r = self.client.get(reverse('cerrar_caja', args=[self.caja.id])).context['r']
        self.assertEqual(r['ventas_total'], 24500)
        self.assertEqual((r['cobros_cantidad'], r['cobros_efectivo'], r['cobros_transferencia']), (3, 10000, 11500))
        self.assertEqual((r['sin_cobro_cantidad'], r['sin_cobro_total']), (1, 3000))
        self.assertEqual(r['esperado_ahora'], 63000)
        h = self.client.get(reverse('caja_hoy'))
        self.assertContains(h, '$63.000')
        self.assertContains(h, 'cj-metodo--mixto')

    def test_cierre_suma_las_transferencias_del_carrito(self):
        self.dia_mezclado()
        # De la venta sin cobro (3.000) entraron 1.000 por transferencia: debería haber 62.000
        r = self.cerrar(self.caja, '62.000', transferencias='1.000', esperado=62000)
        self.assertRedirects(r, reverse('detalle_caja', args=[self.caja.id]))
        c = CajaDiaria.objects.get(pk=self.caja.pk)
        self.assertEqual((c.transferencias, c.esperado, c.diferencia, c.resultado), (12500, 62000, 0, 'cuadra'))
        d = self.client.get(reverse('detalle_caja', args=[c.id]))
        self.assertContains(d, '3 cobros con el carrito')

    def test_lo_escrito_no_pasa_de_lo_vendido_sin_cobro(self):
        self.dia_mezclado()
        r = self.cerrar(self.caja, '0', transferencias='3.001', confirmado=False)
        self.assertContains(r, 'No puede ser más de lo vendido sin cobro ($3.000)')

    def test_todo_por_carrito_no_pregunta_transferencias(self):
        self.cobrar([{'id': self.pan.id, 'cantidad': 2}], 'transferencia')   # 13.000
        r = self.client.get(reverse('cerrar_caja', args=[self.caja.id]))
        self.assertContains(r, 'Todo lo de hoy se cobró con el carrito')
        self.assertNotContains(r, 'id="linea-transf"')
        self.cerrar(self.caja, '50.000', esperado=50000)
        c = CajaDiaria.objects.get(pk=self.caja.pk)
        self.assertEqual((c.transferencias, c.esperado, c.resultado), (13000, 50000, 'cuadra'))

    def test_pagos_a_proveedor_solo_con_el_efectivo_que_hay(self):
        self.cobrar([{'id': self.pan.id, 'cantidad': 2}], 'transferencia')   # entra 13.000 pero no al cajón
        url = reverse('registrar_pago', args=[self.caja.id])
        r = self.client.post(url, {'proveedor': self.proveedor.id, 'valor': '50.001'})
        self.assertContains(r, 'solo debería haber $50.000')
        r = self.client.post(url, {'proveedor': self.proveedor.id, 'valor': '50.000'})
        self.assertRedirects(r, reverse('caja_hoy'))