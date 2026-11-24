import csv
import json
import logging
import re
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Count, F, Sum
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.http import urlencode
from django.views.decorators.http import require_POST

from gestor_inventario.models import Proveedor
from productos.models import Producto, Transaccion
from productos.views import solo_superusuario   # mismo permiso que el resto: solo administrador
from . import resumen as calc
from .forms import AperturaForm, CierreForm, PagoForm
from .models import CajaDiaria, Cobro, CobroItem, PagoProveedor

logger = logging.getLogger(__name__)


def _nombre(usuario):
    return usuario.get_full_name() or usuario.get_username()


def _pesos(valor):
    valor = int(valor or 0)
    texto = f'{abs(valor):,}'.replace(',', '.')
    return f'-${texto}' if valor < 0 else f'${texto}'


def modo_pruebas():
    """Con CAJA_MODO_PRUEBAS = True en settings.py se pueden borrar cierres para probar varias veces."""
    return bool(getattr(settings, 'CAJA_MODO_PRUEBAS', False))


def _pendiente_anterior(hoy):
    """Una caja de un día anterior que quedó abierta (hay que cerrarla antes de abrir la de hoy)."""
    return CajaDiaria.objects.filter(estado=CajaDiaria.ABIERTA, fecha__lt=hoy).order_by('fecha').first()


def _saludo():
    hora = timezone.localtime().hour
    return 'Buenos días' if hora < 12 else 'Buenas tardes' if hora < 19 else 'Buenas noches'


def _contexto_apertura(request, hoy, form):
    ventas_hoy = calc.ventas_del_dia(hoy).aggregate(n=Count('pk'), total=Sum('total'))
    return {
        'saludo': _saludo(),
        'nombre': request.user.first_name.split(' ')[0] if request.user.first_name else '',
        'hoy': hoy, 'caja': None, 'pendiente': _pendiente_anterior(hoy), 'form': form, 'modo_pruebas': modo_pruebas(),
        'ultima': CajaDiaria.objects.filter(estado=CajaDiaria.CERRADA).first(),
        'ventas_sin_caja': ventas_hoy['n'],
        'ventas_sin_caja_total': int(ventas_hoy['total'] or 0),
    }


VENTAS_POR_PAGINA = 5


def _ventas_paginadas(request, fecha):
    """Las ventas del día de 5 en 5, la más reciente primero (?ventas=2 es la segunda página)."""
    ventas = (calc.ventas_del_dia(fecha)
              .select_related('cobro_item__cobro')
              .order_by('-fecha_hora', '-id_transaccion'))
    pagina = Paginator(ventas, VENTAS_POR_PAGINA).get_page(request.GET.get('ventas'))
    return {
        'ventas_pagina': pagina,
        'ventas_rango': list(pagina.paginator.get_elided_page_range(pagina.number, on_each_side=1, on_ends=1)),
    }


def _proveedores_inactivos():
    """Para avisar por qué la lista de proveedores sale vacía."""
    return Proveedor.objects.filter(activo=False).count()


# ============================================================
#  CAJA DE HOY: abrir · ver cómo va · pagos · ir a cerrar
# ============================================================
@solo_superusuario
def caja_hoy(request):
    hoy = timezone.localdate()
    caja = CajaDiaria.objects.filter(fecha=hoy).first()
    contexto = {
        'hoy': hoy,
        'caja': caja,
        'pendiente': _pendiente_anterior(hoy),
        'modo_pruebas': modo_pruebas(),
    }

    if caja is None:
        # Todavía no se abre: formulario de apertura (HU_017)
        contexto.update(_contexto_apertura(request, hoy, AperturaForm()))
    elif caja.esta_abierta:
        r = calc.calcular(caja)
        contexto.update({
            'r': r,
            'pagos': list(caja.pagos.all()),
            'pago_form': PagoForm(),
            'proveedores': PagoForm().proveedores,
            'proveedores_inactivos': _proveedores_inactivos(),
            **_ventas_paginadas(request, hoy),
        })
    else:
        contexto['despues'] = calc.despues_del_cierre(caja)

    return render(request, 'caja/hoy.html', contexto)


@solo_superusuario
@require_POST
def abrir_caja(request):
    hoy = timezone.localdate()
    pendiente = _pendiente_anterior(hoy)
    if pendiente:
        messages.error(request, f'Primero cierra la caja del {date_format(pendiente.fecha, "j \\d\\e F")}.')
        return redirect('caja_hoy')
    if CajaDiaria.objects.filter(fecha=hoy).exists():
        messages.info(request, 'La caja de hoy ya está abierta.')
        return redirect('caja_hoy')

    form = AperturaForm(request.POST)
    if not form.is_valid():
        return render(request, 'caja/hoy.html', _contexto_apertura(request, hoy, form))

    try:
        with transaction.atomic():
            CajaDiaria.objects.create(
                fecha=hoy,
                base_inicial=form.cleaned_data['base_inicial'],
                abierta_por=request.user,
                abierta_por_nombre=_nombre(request.user),
            )
    except IntegrityError:
        # Dos personas abrieron al mismo tiempo: la fecha es única, así que solo queda una
        messages.info(request, 'La caja de hoy ya está abierta.')
        return redirect('caja_hoy')
    except DatabaseError:
        logger.exception('No se pudo abrir la caja')
        messages.error(request, 'No se pudo abrir la caja. Intenta de nuevo.')
        return redirect('caja_hoy')

    messages.success(request, f'Caja abierta con {_pesos(form.cleaned_data["base_inicial"])} de base.')
    return redirect('caja_hoy')


@solo_superusuario
@require_POST
def registrar_pago(request, id):
    with transaction.atomic():
        # select_for_update: si alguien está cerrando la caja en este momento, esperamos a que termine
        caja = get_object_or_404(CajaDiaria.objects.select_for_update(), id=id)
        if not caja.esta_abierta:
            messages.error(request, 'Esa caja ya se cerró; no se le pueden anotar pagos.')
            return redirect('caja_hoy')
        if caja.fecha != timezone.localdate():
            messages.error(request, 'Los pagos se anotan en la caja de hoy. Cierra primero la caja pendiente.')
            return redirect('caja_hoy')

        r = calc.calcular(caja)
        form = PagoForm(request.POST, disponible=r['esperado_ahora'])
        if form.is_valid():
            proveedor, nombre = form.proveedor_y_nombre()
            PagoProveedor.objects.create(
                caja=caja,
                proveedor=proveedor,
                proveedor_nombre=nombre,
                concepto=form.cleaned_data['concepto'].strip(),
                valor=form.cleaned_data['valor'],
                registrado_por=request.user,
                registrado_por_nombre=_nombre(request.user),
            )
            messages.success(request, f'Pago de {_pesos(form.cleaned_data["valor"])} a {nombre} anotado.')
            return redirect('caja_hoy')

    # Con errores: se vuelve a mostrar la caja con el formulario y sus mensajes
    return render(request, 'caja/hoy.html', {
        'hoy': caja.fecha, 'caja': caja, 'pendiente': None,
        'r': r, 'pagos': list(caja.pagos.all()), 'pago_form': form, 'proveedores': form.proveedores,
        'proveedores_inactivos': _proveedores_inactivos(),
        'modo_pruebas': modo_pruebas(),
        **_ventas_paginadas(request, caja.fecha),
        'abrir_pago': True,
    })


@solo_superusuario
@require_POST
def eliminar_pago(request, id):
    with transaction.atomic():
        pago = get_object_or_404(PagoProveedor.objects.select_related('caja'), id=id)
        CajaDiaria.objects.select_for_update().filter(pk=pago.caja_id).first()
        try:
            pago.delete()
        except ValidationError as error:
            messages.error(request, error.messages[0])
            return redirect('caja_hoy')
    messages.success(request, f'Se quitó el pago a {pago.proveedor_nombre}.')
    return redirect('caja_hoy')


@solo_superusuario
@require_POST
def borrar_caja_prueba(request, id):
    """Modo de pruebas: borra una caja (abierta o cerrada) para volver a abrirla y cerrarla."""
    if not modo_pruebas():
        raise Http404('El modo de pruebas está apagado.')
    caja = get_object_or_404(CajaDiaria, id=id)
    fecha = caja.fecha
    caja.borrar_para_pruebas()
    messages.success(request, f'Prueba: se borró la caja del {date_format(fecha, "j \\d\\e F")}. Ya puedes abrirla y cerrarla otra vez.')
    if fecha == timezone.localdate():
        return redirect('caja_hoy')
    return redirect('historial_cajas')


# ============================================================
#  CIERRE (HU_018): datos → confirmar → guardar
# ============================================================
def _contado_escrito(form):
    """El dinero contado que ya se escribió (y es válido). Desde ahí ya no se puede cambiar, solo la observación."""
    if form.is_bound:
        if 'contado' in form.errors:
            return None
        return getattr(form, 'cleaned_data', {}).get('contado')
    valor = form.initial.get('contado')
    if valor in (None, ''):
        return None
    try:
        return form.fields['contado'].clean(valor)
    except ValidationError:
        return None


def _contexto_cierre(caja, r, form, **extra):
    contexto = {
        'caja': caja, 'r': r, 'form': form, 'pagos': list(caja.pagos.all()), 'paso': 'datos',
        'contado_fijo': _contado_escrito(form),
    }
    contexto.update(extra)
    return contexto


@solo_superusuario
def cerrar_caja(request, id):
    caja = get_object_or_404(CajaDiaria, id=id)
    if not caja.esta_abierta:
        messages.info(request, 'Esa caja ya está cerrada.')
        return redirect('detalle_caja', id=caja.id)

    r = calc.calcular(caja)

    if request.method != 'POST':
        return render(request, 'caja/cerrar.html', _contexto_cierre(caja, r, CierreForm(resumen=r)))

    # «Corregir» desde la confirmación: vuelve al formulario con lo que había escrito
    if 'corregir' in request.POST:
        inicial = {k: request.POST.get(k, '') for k in ('contado', 'observacion')}
        return render(request, 'caja/cerrar.html', _contexto_cierre(caja, r, CierreForm(initial=inicial, resumen=r)))

    form = CierreForm(request.POST, resumen=r)
    confirmando = request.POST.get('confirmado') == '1'
    if not form.is_valid():
        # Si ya venía de confirmar y ahora no pasa, es porque cambiaron los números (p. ej. una venta nueva)
        return render(request, 'caja/cerrar.html', _contexto_cierre(caja, r, form, cambio=confirmando))

    datos = form.cleaned_data
    cambio = confirmando and str(datos['esperado']) != request.POST.get('esperado_visto', '')
    if not confirmando or cambio:
        # Paso 2: se muestra todo y se pide confirmar (HU_018, criterio 7)
        return render(request, 'caja/cerrar.html', _contexto_cierre(
            caja, r, form, paso='confirmar', datos=datos, cambio=cambio,
            resultado=CajaDiaria.resultado_de(datos['diferencia']),
        ))

    # Paso 3: guardar. Se recalcula TODO en este instante y se bloquea la fila para que
    # nadie más la cierre o le meta un pago mientras tanto.
    try:
        with transaction.atomic():
            caja = CajaDiaria.objects.select_for_update().get(pk=caja.pk)
            if not caja.esta_abierta:
                messages.info(request, 'Esa caja ya la cerró otra persona.')
                return redirect('detalle_caja', id=caja.id)

            ahora = timezone.now()
            r = calc.calcular(caja, hasta=ahora)
            form = CierreForm(request.POST, resumen=r)
            visto = request.POST.get('esperado_visto', '')
            if not form.is_valid() or str(form.cleaned_data['esperado']) != visto:
                # Mientras revisaba entró una venta o un pago: se muestra de nuevo con los números nuevos
                if form.is_valid():
                    datos = form.cleaned_data
                    return render(request, 'caja/cerrar.html', _contexto_cierre(
                        caja, r, form, paso='confirmar', datos=datos, cambio=True,
                        resultado=CajaDiaria.resultado_de(datos['diferencia']),
                    ))
                return render(request, 'caja/cerrar.html', _contexto_cierre(caja, r, form, cambio=True))

            datos = form.cleaned_data
            for campo in (
                'ventas_total', 'ventas_cantidad', 'ventas_unidades',
                'consumos_total', 'consumos_cantidad',
                'salidas_perdida_total', 'salidas_perdida_unidades', 'salidas_cambio_total', 'salidas_cantidad',
                'pagos_proveedor_total', 'pagos_proveedor_cantidad',
            ):
                setattr(caja, campo, r[campo])
            caja.transferencias = datos['transferencias_total']
            caja.esperado = datos['esperado']
            caja.contado = datos['contado']
            caja.diferencia = datos['diferencia']
            caja.resultado = CajaDiaria.resultado_de(datos['diferencia'])
            caja.observacion = datos['observacion']
            caja.cerrada_por = request.user
            caja.cerrada_por_nombre = _nombre(request.user)
            caja.cerrada_en = ahora
            caja.estado = CajaDiaria.CERRADA
            caja.save()
    except DatabaseError:
        logger.exception('No se pudo cerrar la caja %s', id)
        messages.error(request, 'No se pudo cerrar la caja. Intenta de nuevo.')
        return redirect('cerrar_caja', id=id)

    textos = {
        CajaDiaria.CUADRA: 'La caja cuadró.',
        CajaDiaria.SOBRANTE: f'Caja cerrada con un sobrante de {_pesos(caja.diferencia)}.',
        CajaDiaria.FALTANTE: f'Caja cerrada con un faltante de {_pesos(abs(caja.diferencia))}.',
    }
    messages.success(request, textos[caja.resultado])
    return redirect('detalle_caja', id=caja.id)


# ============================================================
#  DETALLE de un cierre (HU_019, criterios 4 y 5)
# ============================================================
@solo_superusuario
def detalle_caja(request, id):
    caja = get_object_or_404(CajaDiaria, id=id)
    if caja.esta_abierta:
        if caja.fecha == timezone.localdate():
            return redirect('caja_hoy')
        return redirect('cerrar_caja', id=caja.id)

    hasta = caja.cerrada_en
    ventas = calc.ventas_del_dia(caja.fecha, hasta)
    top = list(
        ventas.values('nom_producto')
        .annotate(unidades=Sum('cantidad'), total=Sum('total'))
        .order_by('-total', 'nom_producto')
    )
    consumos = list(
        calc.consumos_del_dia(caja.fecha, hasta).values('persona')
        .annotate(total=Sum('total'), n=Count('pk')).order_by('-total')
    )
    salidas = list(
        calc.salidas_del_dia(caja.fecha, hasta).values('motivo_nombre', 'aplica_cambio')
        .annotate(unidades=Sum('cantidad'), valor=Sum(calc.VALOR_SALIDA), n=Count('pk'))
        .order_by('aplica_cambio', '-valor')
    )
    # Largo de la barrita de cada producto (el que más vendió = 100)
    mayor = top[0]['total'] if top else 0
    for t in top:
        t['pct'] = round(t['total'] * 100 / mayor) if mayor else 0

    return render(request, 'caja/detalle.html', {
        'caja': caja,
        'modo_pruebas': modo_pruebas(),
        'pagos': list(caja.pagos.all()),
        'top': top[:8],
        'top_resto': len(top) - 8 if len(top) > 8 else 0,
        'ventas': list(ventas.select_related('cobro_item__cobro').order_by('fecha_hora', 'id_transaccion')[:500]),
        'cobros': calc.cobros_de(ventas).aggregate(n=Count('pk'), efectivo=Sum('efectivo'), transferencia=Sum('transferencia'), vuelto=Sum('vuelto')),
        'consumos': consumos,
        'salidas': salidas,
        'despues': calc.despues_del_cierre(caja),
        'anterior': CajaDiaria.objects.filter(estado=CajaDiaria.CERRADA, fecha__lt=caja.fecha).order_by('-fecha').first(),
        'siguiente': CajaDiaria.objects.filter(estado=CajaDiaria.CERRADA, fecha__gt=caja.fecha).order_by('fecha').first(),
    })


# ============================================================
#  HISTORIAL (HU_019): lista de cierres filtrada por mes y por día, paginada, y CSV
# ============================================================
POR_PAGINA = 10


@solo_superusuario
def historial_cajas(request):
    cerradas = CajaDiaria.objects.filter(estado=CajaDiaria.CERRADA)
    meses = list(cerradas.dates('fecha', 'month', order='DESC'))

    # ?dia=2026-11-23 (si viene solo el día, el mes sale de ahí)
    dia, dia_fecha = request.GET.get('dia', ''), None
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', dia):
        dia_fecha = cerradas.filter(fecha=dia).values_list('fecha', flat=True).first() if _fecha_valida(dia) else None
    mes = f'{dia_fecha:%Y-%m}' if dia_fecha else request.GET.get('mes', '')
    mes_fecha = next((m for m in meses if f'{m:%Y-%m}' == mes), None) if re.fullmatch(r'\d{4}-\d{2}', mes) else None
    if mes_fecha is None:
        mes, dia_fecha = '', None
    dia = f'{dia_fecha:%Y-%m-%d}' if dia_fecha else ''

    lista, dias = cerradas, []
    if mes_fecha:
        lista = cerradas.filter(fecha__year=mes_fecha.year, fecha__month=mes_fecha.month)
        dias = list(lista.dates('fecha', 'day', order='DESC'))
    if dia_fecha:
        lista = lista.filter(fecha=dia_fecha)

    if request.GET.get('formato') == 'csv':
        return _csv(lista, dia or mes)

    pagina = Paginator(lista, POR_PAGINA).get_page(request.GET.get('pagina'))
    filtros = {k: v for k, v in (('mes', mes), ('dia', dia)) if v}
    return render(request, 'caja/historial.html', {
        'pagina': pagina,
        'cajas': pagina.object_list,
        'rango_paginas': pagina.paginator.get_elided_page_range(pagina.number, on_each_side=1, on_ends=1),
        'base_qs': urlencode(filtros),
        'csv_qs': urlencode({**filtros, 'formato': 'csv'}),
        'meses': [{'valor': f'{m:%Y-%m}', 'texto': date_format(m, 'F Y')} for m in meses],
        'mes': mes,
        'dias': [{'valor': f'{d:%Y-%m-%d}', 'texto': date_format(d, 'l j')} for d in dias],
        'dia': dia,
        'total_cierres': cerradas.count(),
        'hay_filtro': bool(filtros),
    })


def _fecha_valida(texto):
    try:
        datetime.strptime(texto, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def _celda(texto):
    # Evita que Excel tome un texto que empieza por = + - @ como una fórmula
    texto = ' '.join(str(texto or '').split())
    return "'" + texto if texto[:1] in ('=', '+', '-', '@') else texto


def _csv(cajas, mes):
    nombre = f'cierres_{mes or "todos"}.csv'
    respuesta = HttpResponse(content_type='text/csv; charset=utf-8')
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre}"'
    respuesta.write('﻿')   # para que Excel lea bien las tildes
    escritor = csv.writer(respuesta, delimiter=';')
    escritor.writerow([
        'Fecha', 'Base', 'Total vendido', 'N° ventas', 'Unidades', 'Transferencias', 'Pagos a proveedores',
        'Esperado', 'Contado', 'Diferencia', 'Resultado', 'Consumos', 'Salidas sin cambio (pérdida)',
        'Salidas con cambio', 'Abrió', 'Cerró', 'Hora de cierre', 'Observación',
    ])
    for c in cajas:
        escritor.writerow([
            c.fecha.strftime('%d/%m/%Y'), c.base_inicial, c.ventas_total, c.ventas_cantidad, c.ventas_unidades,
            c.transferencias, c.pagos_proveedor_total, c.esperado, c.contado, c.diferencia,
            c.get_resultado_display(), c.consumos_total, c.salidas_perdida_total, c.salidas_cambio_total,
            _celda(c.abierta_por_nombre), _celda(c.cerrada_por_nombre),
            timezone.localtime(c.cerrada_en).strftime('%H:%M') if c.cerrada_en else '',
            _celda(c.observacion),
        ])
    return respuesta


# ============================================================
#  COBRAR EL CARRITO (desde la lista de productos)
#  Recibe los productos y cómo pagaron; en UNA sola operación descuenta el stock,
#  crea una venta (Transaccion) por producto y guarda el cobro. Si algo falla, no queda nada.
# ============================================================
MAX_LINEAS = 200


def _entero(valor):
    """Número entero >= 0 que venga del navegador (texto o número). None si no sirve."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, int):
        return valor if valor >= 0 else None
    texto = str(valor if valor is not None else '').replace('.', '').replace('$', '').strip()
    return int(texto) if texto.isdigit() and len(texto) <= 12 else None


def _error(mensaje, **extra):
    return JsonResponse({'ok': False, 'mensaje': mensaje, **extra}, status=400)


@solo_superusuario
@require_POST
def cobrar_carrito(request):
    try:
        datos = json.loads(request.body or b'{}')
    except (ValueError, UnicodeDecodeError):
        return _error('No se pudo leer el carrito. Recarga la página e intenta de nuevo.')
    if not isinstance(datos, dict):
        return _error('No se pudo leer el carrito.')

    # 1) Productos y cantidades (si un producto viene repetido se suman)
    lineas = datos.get('items')
    if not isinstance(lineas, list) or not lineas:
        return _error('El carrito está vacío.')
    if len(lineas) > MAX_LINEAS:
        return _error('Son demasiados productos para un solo cobro.')
    pedido = {}
    for linea in lineas:
        if not isinstance(linea, dict):
            return _error('No se pudo leer el carrito.')
        pid, cantidad = _entero(linea.get('id')), _entero(linea.get('cantidad'))
        if not pid or not cantidad or cantidad > 99999:
            return _error('Cada producto del carrito debe tener una cantidad de 1 en adelante.')
        pedido[pid] = pedido.get(pid, 0) + cantidad

    # 2) Cómo paga
    metodo = datos.get('metodo')
    if metodo not in dict(Cobro.METODOS):
        return _error('Elige cómo paga: efectivo, transferencia o las dos.')
    efectivo_parte = _entero(datos.get('efectivo'))
    recibido = _entero(datos.get('recibido')) if datos.get('recibido') not in (None, '') else None

    try:
        with transaction.atomic():
            # Se bloquean las filas de esos productos (en orden, para que dos cobros a la vez no se traben)
            productos = {p.pk: p for p in Producto.objects.select_for_update().filter(pk__in=sorted(pedido)).order_by('pk')}
            if len(productos) != len(pedido):
                return _error('Uno de los productos ya no existe. Quítalo del carrito.',
                              no_existen=[pid for pid in pedido if pid not in productos])

            faltan = {pid: productos[pid].existencias for pid, n in pedido.items() if productos[pid].existencias < n}
            if faltan:
                nombres = ', '.join(f'{productos[pid].nombre} (quedan {max(q, 0)})' for pid, q in faltan.items())
                return _error(f'No alcanza: {nombres}.',
                              existencias={str(pid): p.existencias for pid, p in productos.items()})

            total = sum(int(productos[pid].precio_unitario) * n for pid, n in pedido.items())

            # 3) Revisar el pago con el total real (los precios salen de la base, no del navegador)
            vuelto = 0
            if metodo == Cobro.EFECTIVO:
                efectivo, transferencia = total, 0
                if recibido is not None:
                    if recibido < total:
                        return _error(f'Con ${recibido:,} no alcanza: faltan ${total - recibido:,}.'.replace(',', '.'))
                    vuelto = recibido - total
            elif metodo == Cobro.TRANSFERENCIA:
                efectivo, transferencia, recibido = 0, total, None
            else:
                if efectivo_parte is None or efectivo_parte <= 0 or efectivo_parte >= total:
                    return _error(
                        f'En pago mixto la parte en efectivo debe ser mayor que $0 y menor que ${total:,}.'.replace(',', '.')
                    )
                efectivo, transferencia = efectivo_parte, total - efectivo_parte
                if recibido is not None:
                    if recibido < efectivo:
                        return _error(f'Con ${recibido:,} no alcanza para la parte en efectivo.'.replace(',', '.'))
                    vuelto = recibido - efectivo

            # 4) Guardar: descontar stock, una venta por producto y el cobro que las une
            ahora = timezone.now()
            ventas = []
            for pid in sorted(pedido):
                producto, cantidad = productos[pid], pedido[pid]
                Producto.objects.filter(pk=pid).update(existencias=F('existencias') - cantidad)
                ventas.append(Transaccion.objects.create(
                    nom_producto=producto.nombre, precio=producto.precio_unitario,
                    cantidad=cantidad, fecha_hora=ahora,
                ))
            cobro = Cobro.objects.create(
                metodo=metodo, total=total, efectivo=efectivo, transferencia=transferencia,
                recibido=recibido, vuelto=vuelto, creado_en=ahora,
                registrado_por=request.user, registrado_por_nombre=_nombre(request.user),
            )
            CobroItem.objects.bulk_create([CobroItem(cobro=cobro, transaccion=v) for v in ventas])
    except DatabaseError:
        logger.exception('No se pudo registrar el cobro')
        return _error('No se pudo registrar el cobro y no se descontó nada. Intenta de nuevo.')

    existencias = dict(Producto.objects.filter(pk__in=pedido).values_list('pk', 'existencias'))
    hoy = timezone.localdate()
    caja_abierta = CajaDiaria.objects.filter(fecha=hoy, estado=CajaDiaria.ABIERTA).exists()

    partes = {
        Cobro.EFECTIVO: f'{_pesos(total)} en efectivo',
        Cobro.TRANSFERENCIA: f'{_pesos(total)} por transferencia',
        Cobro.MIXTO: f'{_pesos(efectivo)} en efectivo y {_pesos(transferencia)} por transferencia',
    }
    mensaje = f'Cobrado: {partes[metodo]}.'
    if vuelto:
        mensaje += f' Vuelto: {_pesos(vuelto)}.'
    if not caja_abierta:
        mensaje += ' Ojo: la caja de hoy no está abierta.'
    return JsonResponse({
        'ok': True,
        'mensaje': mensaje,
        'cobro': {'id': cobro.pk, 'total': total, 'efectivo': efectivo, 'transferencia': transferencia, 'vuelto': vuelto},
        'existencias': {str(k): v for k, v in existencias.items()},
        'caja_abierta': caja_abierta,
    })