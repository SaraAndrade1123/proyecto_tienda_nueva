
from decimal import Decimal

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.shortcuts import render
from django.utils.dateparse import parse_date

from accounts.views import es_superadmin as es_admin
from productos.models import Transaccion

from .models import Consumo


CERO = Decimal('0')


def _fecha(texto):
    """Convierte AAAA-MM-DD en una fecha válida."""
    try:
        return parse_date(texto)
    except (ValueError, TypeError):
        return None


@login_required
@user_passes_test(es_admin)
def informe_ingresos(request):

    fecha_inicio = request.GET.get('fecha_inicio', '').strip()
    fecha_fin = request.GET.get('fecha_fin', '').strip()

    contexto = {
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'generado': False,
        'error': None,
        'sin_ventas': False,
    }

    # Primera visita: mostrar únicamente el formulario.
    if 'generar' not in request.GET:
        return render(request, 'reportes/informe_ingresos.html', contexto)

    # Validar fechas.
    if not fecha_inicio or not fecha_fin:
        contexto['error'] = (
            'Selecciona la fecha de inicio y la fecha de fin.'
        )
        return render(request, 'reportes/informe_ingresos.html', contexto)

    inicio = _fecha(fecha_inicio)
    fin = _fecha(fecha_fin)

    if inicio is None or fin is None:
        contexto['error'] = (
            'Fecha inválida. Revisa las fechas seleccionadas.'
        )
        return render(request, 'reportes/informe_ingresos.html', contexto)

    if inicio > fin:
        contexto['error'] = (
            'La fecha de inicio no puede ser posterior a la fecha de fin.'
        )
        return render(request, 'reportes/informe_ingresos.html', contexto)

    contexto.update({
        'generado': True,
        'inicio': inicio,
        'fin': fin,
    })

    # Consultar las ventas reales registradas en Tienda Nueva.
    transacciones = Transaccion.objects.filter(
        fecha_hora__date__range=(inicio, fin)
    )

    cantidad_pedidos = transacciones.count()

    if cantidad_pedidos == 0:
        contexto['sin_ventas'] = True
        return render(
            request,
            'reportes/informe_ingresos.html',
            contexto
        )

    # Sumar el valor total de las transacciones.
    total_ventas = (
        transacciones.aggregate(total=Sum('total'))['total'] or CERO
    )

    # Consultar los consumos personales del mismo período.
    total_consumos = (
        Consumo.objects.filter(
            fecha__date__range=(inicio, fin)
        ).aggregate(total=Sum('valor'))['total'] or CERO
    )

    # Obtener los cinco productos con más unidades vendidas.
    top_productos = (
        transacciones.values('nom_producto')
        .annotate(
            unidades=Sum('cantidad'),
            total=Sum('total'),
        )
        .order_by('-unidades', '-total')[:5]
    )

    contexto.update({
        'total_ventas': total_ventas,
        'total_consumos': total_consumos,
        'total_neto': total_ventas - total_consumos,
        'cantidad_pedidos': cantidad_pedidos,
        'top_productos': top_productos,
    })

    return render(
        request,
        'reportes/informe_ingresos.html',
        contexto
    )
