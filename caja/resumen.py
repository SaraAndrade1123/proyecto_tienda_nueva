"""
Cálculos del día. Aquí está TODO lo que la app lee de las otras apps (solo lectura):

- productos.Transaccion           -> ventas
- gestor_inventario.ConsumoPersonal -> consumos personales (solo los activos)
- salidas.SalidaProducto          -> salidas de inventario (con y sin cambio del proveedor)

Ninguna de esas tablas se modifica desde la caja. Los cobros del carrito (cómo se pagó cada venta)
sí son de esta app: tabla Cobro.
"""
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum

from gestor_inventario.models import ConsumoPersonal
from productos.models import Transaccion
from salidas.models import SalidaProducto


def _entero(valor):
    return int(valor or 0)


def ventas_del_dia(fecha, hasta=None):
    ventas = Transaccion.objects.filter(fecha_hora__date=fecha)
    if hasta is not None:
        ventas = ventas.filter(fecha_hora__lte=hasta)
    return ventas


def cobros_de(ventas):
    """Los cobros del carrito que pagaron esas ventas."""
    from .models import CobroItem, Cobro
    return Cobro.objects.filter(pk__in=CobroItem.objects.filter(transaccion__in=ventas).values('cobro_id'))


def consumos_del_dia(fecha, hasta=None):
    consumos = ConsumoPersonal.objects.filter(activo=True, fecha=fecha)
    if hasta is not None:
        consumos = consumos.filter(creado_en__lte=hasta)
    return consumos


def salidas_del_dia(fecha, hasta=None):
    salidas = SalidaProducto.objects.filter(fecha=fecha)
    if hasta is not None:
        salidas = salidas.filter(creado_en__lte=hasta)
    return salidas


VALOR_SALIDA = ExpressionWrapper(
    F('cantidad') * F('precio_unitario'), output_field=DecimalField(max_digits=16, decimal_places=0),
)


def calcular(caja, hasta=None):
    """
    Resumen del día de esa caja. `hasta` deja por fuera lo que se registró después
    (se usa para el cierre y para el detalle de una caja ya cerrada).
    """
    ventas = ventas_del_dia(caja.fecha, hasta)
    v = ventas.aggregate(total=Sum('total'), n=Count('pk'), unidades=Sum('cantidad'))
    # Cómo se pagó: lo que pasó por el carrito ya trae efectivo y transferencia;
    # las ventas «sin cobro» (vendidas de otra forma) no dicen cómo se pagaron.
    co = cobros_de(ventas).aggregate(efectivo=Sum('efectivo'), transferencia=Sum('transferencia'), n=Count('pk'))
    sc = ventas.filter(cobro_item__isnull=True).aggregate(total=Sum('total'), n=Count('pk'))
    c = consumos_del_dia(caja.fecha, hasta).aggregate(total=Sum('total'), n=Count('pk'))
    s = salidas_del_dia(caja.fecha, hasta).aggregate(
        perdida=Sum(VALOR_SALIDA, filter=Q(aplica_cambio=False)),
        perdida_u=Sum('cantidad', filter=Q(aplica_cambio=False)),
        cambio=Sum(VALOR_SALIDA, filter=Q(aplica_cambio=True)),
        n=Count('pk'),
    )
    p = caja.pagos.aggregate(total=Sum('valor'), n=Count('pk'))

    resumen = {
        'base_inicial': caja.base_inicial,
        'ventas_total': _entero(v['total']),
        'ventas_cantidad': v['n'],
        'ventas_unidades': _entero(v['unidades']),
        'consumos_total': _entero(c['total']),
        'consumos_cantidad': c['n'],
        'salidas_perdida_total': _entero(s['perdida']),
        'salidas_perdida_unidades': _entero(s['perdida_u']),
        'salidas_cambio_total': _entero(s['cambio']),
        'salidas_cantidad': s['n'],
        'pagos_proveedor_total': _entero(p['total']),
        'pagos_proveedor_cantidad': p['n'],
        'cobros_cantidad': co['n'],
        'cobros_efectivo': _entero(co['efectivo']),
        'cobros_transferencia': _entero(co['transferencia']),
        'sin_cobro_total': _entero(sc['total']),
        'sin_cobro_cantidad': sc['n'],
    }
    # Lo que debería haber en el cajón si TODAS las ventas fueron en efectivo
    resumen['esperado_sin_transferencias'] = (
        resumen['base_inicial'] + resumen['ventas_total'] - resumen['pagos_proveedor_total']
    )
    # …y descontando lo que ya se sabe que entró por transferencia (cobros del carrito)
    resumen['esperado_ahora'] = resumen['esperado_sin_transferencias'] - resumen['cobros_transferencia']
    return resumen


def despues_del_cierre(caja):
    """HU_018, criterio 9: lo que se registró con la fecha de esa caja DESPUÉS de cerrarla."""
    if not caja.cerrada_en:
        return None
    ventas = Transaccion.objects.filter(fecha_hora__date=caja.fecha, fecha_hora__gt=caja.cerrada_en)
    v = ventas.aggregate(total=Sum('total'), n=Count('pk'))
    consumos = ConsumoPersonal.objects.filter(activo=True, fecha=caja.fecha, creado_en__gt=caja.cerrada_en).count()
    salidas = SalidaProducto.objects.filter(fecha=caja.fecha, creado_en__gt=caja.cerrada_en).count()
    if not (v['n'] or consumos or salidas):
        return None
    return {'ventas': v['n'], 'ventas_total': _entero(v['total']), 'consumos': consumos, 'salidas': salidas}