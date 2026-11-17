from decimal import Decimal

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.shortcuts import render
from django.utils.dateparse import parse_date

from accounts.views import es_superadmin as es_admin

from .models import Consumo, DetallePedido, Pedido

CERO = Decimal('0')


def _fecha(texto):
    """Convierte 'AAAA-MM-DD' en date. Devuelve None si no es válida."""
    try:
        return parse_date(texto)
    except ValueError:
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

    # Primera visita: solo se muestra el formulario.
    if 'generar' not in request.GET:
        return render(request, 'reportes/informe_ingresos.html', contexto)

    # ---- Validaciones ----
    if not fecha_inicio or not fecha_fin:
        contexto['error'] = 'Selecciona la fecha de inicio y la fecha de fin.'
        return render(request, 'reportes/informe_ingresos.html', contexto)

    inicio = _fecha(fecha_inicio)
    fin = _fecha(fecha_fin)

    if inicio is None or fin is None:
        contexto['error'] = 'Fecha inválida. Revisa las fechas seleccionadas.'
        return render(request, 'reportes/informe_ingresos.html', contexto)

    if inicio > fin:
        contexto['error'] = 'La fecha de inicio no puede ser posterior a la fecha de fin.'
        return render(request, 'reportes/informe_ingresos.html', contexto)

    # ---- Cálculos ----
    contexto.update({'generado': True, 'inicio': inicio, 'fin': fin})

    pedidos = Pedido.objects.filter(
        estado='completado',
        fecha__date__range=(inicio, fin),
    )
    cantidad_pedidos = pedidos.count()

    if cantidad_pedidos == 0:
        contexto['sin_ventas'] = True
        return render(request, 'reportes/informe_ingresos.html', contexto)

    linea = ExpressionWrapper(
        F('cantidad') * F('precio_unitario'),
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )

    detalles = DetallePedido.objects.filter(pedido__in=pedidos)

    total_ventas = detalles.aggregate(t=Sum(linea))['t'] or CERO

    total_consumos = Consumo.objects.filter(
        fecha__date__range=(inicio, fin)
    ).aggregate(t=Sum('valor'))['t'] or CERO

    top_productos = (
        detalles.values('producto__nombre')
        .annotate(unidades=Sum('cantidad'), total=Sum(linea))
        .order_by('-unidades', '-total')[:5]
    )

    contexto.update({
        'total_ventas': total_ventas,
        'total_consumos': total_consumos,
        'total_neto': total_ventas - total_consumos,
        'cantidad_pedidos': cantidad_pedidos,
        'top_productos': top_productos,
    })

    return render(request, 'reportes/informe_ingresos.html', contexto)