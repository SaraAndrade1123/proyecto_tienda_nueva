from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date

from accounts.views import es_superadmin as es_admin
from productos.models import Transaccion
from salidas.models import SalidaProducto
from gestor_inventario.models import ConsumoPersonal  # confirma que esta sea la ruta

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

    # Primera visita: solo se muestra el formulario (no se consulta nada).
    if 'generar' not in request.GET:
        return render(request, 'reportes/informe_ingresos.html', contexto)

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

    contexto.update({'generado': True, 'inicio': inicio, 'fin': fin})

    # Rango por fecha_hora (usa el índice, a diferencia de __date): [inicio 00:00, fin+1 00:00)
    zona = timezone.get_current_timezone()
    desde = timezone.make_aware(datetime.combine(inicio, time.min), zona)
    hasta = timezone.make_aware(datetime.combine(fin + timedelta(days=1), time.min), zona)

    # ---- Ventas (una sola consulta agregada) ----
    ventas = Transaccion.objects.filter(fecha_hora__gte=desde, fecha_hora__lt=hasta)
    resumen = ventas.aggregate(total=Sum('total'), n=Count('pk'))
    cantidad_ventas = resumen['n']

    if cantidad_ventas == 0:
        contexto['sin_ventas'] = True
        return render(request, 'reportes/informe_ingresos.html', contexto)

    total_ventas = resumen['total'] or CERO

    top_productos = (
        ventas.values('nom_producto')
        .annotate(unidades=Sum('cantidad'), total=Sum('total'))
        .order_by('-unidades', '-total')[:5]
    )

    # ---- Consumos personales ----
    total_consumos = ConsumoPersonal.objects.filter(
        activo=True, fecha__range=(inicio, fin)
    ).aggregate(t=Sum('total'))['t'] or CERO

    # ---- Salidas (vencidos, dañados, pérdidas) ----
    valor_salida = ExpressionWrapper(
        F('cantidad') * F('precio_unitario'),
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )
    salidas = SalidaProducto.objects.filter(fecha__range=(inicio, fin))
    por_cambio = {
        fila['aplica_cambio']: fila['t']
        for fila in salidas.values('aplica_cambio').annotate(t=Sum(valor_salida))
    }
    total_perdidas = por_cambio.get(False) or CERO
    por_recuperar = por_cambio.get(True) or CERO

    contexto.update({
        'total_ventas': total_ventas,
        'total_consumos': total_consumos,
        'total_perdidas': total_perdidas,
        'por_recuperar': por_recuperar,
        'total_neto': total_ventas - total_consumos - total_perdidas,
        'cantidad_pedidos': cantidad_ventas,
        'top_productos': list(top_productos),
    })

    return render(request, 'reportes/informe_ingresos.html', contexto)