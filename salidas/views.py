import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import DatabaseError, transaction
from django.db.models import Count, F, ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from productos.models import Producto
from productos.views import solo_superusuario
from .forms import MotivoForm, SalidaForm, fotos_habilitadas
from .models import MOTIVOS_BASE, MotivoSalida, SalidaProducto

logger = logging.getLogger(__name__)

HISTORIAL_MAX = 300   # cuántos retiros se cargan en la ventana del historial
POR_PAGINA = (10, 20, 50)   # opciones de «Mostrar» en la lista de productos


def _pesos(valor):
    return '$' + f'{int(valor or 0):,}'.replace(',', '.')


# ============================================================
#  INICIO: los productos en tarjetas + ventana con el historial
# ============================================================
@solo_superusuario
def lista_salidas(request):
    # El filtro va en vivo en el navegador; esto es solo por si alguien busca sin JavaScript (escribe y Enter).
    busqueda = request.GET.get('buscar', '').strip()[:100]
    productos = Producto.objects.filter(existencias__gt=0).select_related('categoria')
    if busqueda:
        productos = productos.filter(nombre__icontains=busqueda)

    # Cuántos por página: solo 10, 20 o 50 (cualquier otro valor vuelve a 10)
    por = request.GET.get('por', '')
    por = int(por) if por in ('10', '20', '50') else POR_PAGINA[0]

    if request.GET.get('todos') == '1':
        # El buscador en vivo pide esto UNA vez para poder buscar en todos los productos, no solo en la página
        pagina, filas, rango = None, productos, []
    else:
        pagina = Paginator(productos, por).get_page(request.GET.get('pagina'))
        filas = pagina.object_list
        rango = pagina.paginator.get_elided_page_range(pagina.number, on_each_side=1, on_ends=1)

    historial = list(SalidaProducto.objects.select_related('producto')[:HISTORIAL_MAX])
    return render(request, 'salidas/lista.html', {
        'filas': filas,
        'pagina': pagina,
        'rango_paginas': rango,
        'por': por,
        'opciones_por': POR_PAGINA,
        'busqueda': busqueda,
        'total_productos': Producto.objects.count(),
        'historial': historial,
        'ultimo': historial[0] if historial else None,
        'total_retiros': SalidaProducto.objects.count(),
        'historial_max': HISTORIAL_MAX,
    })


# ============================================================
#  REGISTRAR UNA SALIDA (descuenta el inventario)
# ============================================================
@solo_superusuario
def registrar_salida(request):
    if request.method == 'POST':
        formulario = SalidaForm(request.POST, request.FILES)
        if formulario.is_valid():
            producto = formulario.cleaned_data['producto']
            cantidad = formulario.cleaned_data['cantidad']
            try:
                # Todo o nada: si algo falla, ni se descuenta el stock ni queda el registro.
                with transaction.atomic():
                    # Igual que en las ventas: UNA sola instrucción que solo descuenta si alcanza,
                    # así dos personas a la vez nunca dejan el stock en negativo.
                    filas = Producto.objects.filter(
                        pk=producto.pk, existencias__gte=cantidad
                    ).update(existencias=F('existencias') - cantidad)
                    if filas == 0:
                        producto.refresh_from_db()
                        formulario.add_error('cantidad', f'No alcanza: de {producto.nombre} solo quedan {producto.existencias}.')
                        raise _SinStock()
                    producto.refresh_from_db()
                    salida = formulario.save(commit=False)
                    salida.nom_producto = producto.nombre
                    salida.precio_unitario = producto.precio_unitario
                    salida.registrado_por = request.user
                    salida.registrado_por_nombre = request.user.get_full_name() or request.user.username
                    salida.save()
            except _SinStock:
                pass
            except DatabaseError:
                logger.exception('No se pudo registrar la salida de %s', producto.nombre)
                messages.error(request, 'No se pudo registrar la salida y no se descontó nada. '
                                        'Si es la primera vez, falta ejecutar «python manage.py migrate».')
            else:
                cambio = 'El proveedor SÍ da cambio.' if salida.aplica_cambio else 'El proveedor NO da cambio.'
                messages.success(request, f'Salida registrada: {cantidad} de {producto.nombre}. '
                                          f'Quedan {producto.existencias}. {cambio}')
                return redirect('detalle_salida', id=salida.id)
    else:
        inicial = {}
        if request.GET.get('producto', '').isdigit():
            inicial['producto'] = request.GET['producto']
        formulario = SalidaForm(initial=inicial)

    # Si el producto ya viene elegido (desde la tarjeta), se muestra su ficha en lugar de la lista.
    elegido_id = str(formulario['producto'].value() or '')
    producto_elegido = None
    if elegido_id.isdigit():
        producto_elegido = formulario.fields['producto'].queryset.filter(pk=elegido_id).first()

    return render(request, 'salidas/registrar.html', {
        'formulario': formulario,
        'producto_elegido': producto_elegido,
        'fotos_habilitadas': fotos_habilitadas(),
        'hay_motivos': MotivoSalida.objects.exists(),
        'motivos_con_cambio': [str(pk) for pk in MotivoSalida.objects.filter(da_cambio=True).values_list('pk', flat=True)],
        'existencias': {p.pk: p.existencias for p in formulario.fields['producto'].queryset},
    })


class _SinStock(Exception):
    """Interna: corta la transacción cuando otra persona se llevó las unidades primero."""


# ============================================================
#  DETALLE DE UNA SALIDA
# ============================================================
@solo_superusuario
def detalle_salida(request, id):
    salida = get_object_or_404(SalidaProducto.objects.select_related('producto', 'registrado_por'), id=id)
    return render(request, 'salidas/detalle.html', {
        'salida': salida,
        'valor_perdido': _pesos(salida.valor_perdido),
        'precio': _pesos(salida.precio_unitario),
    })


# ============================================================
#  MOTIVOS (como las categorías, pero todo en una sola pantalla)
# ============================================================
@solo_superusuario
def motivos_salida(request):
    if request.method == 'POST':
        formulario = MotivoForm(request.POST)
        if formulario.is_valid():
            motivo = formulario.save()
            messages.success(request, f'Motivo «{motivo.nombre}» agregado.')
            return redirect('motivos_salida')
    else:
        formulario = MotivoForm()

    motivos = MotivoSalida.objects.annotate(usos=Count('salidas'))
    return render(request, 'salidas/motivos.html', {
        'formulario': formulario,
        'motivos': motivos,
        'con_cambio': sum(1 for m in motivos if m.da_cambio),
        'motivos_base': MOTIVOS_BASE,
    })


@solo_superusuario
@require_POST
def cargar_motivos_salida(request):
    """Crea de un clic los 7 motivos de la HU (los que ya existan no se repiten)."""
    creados = 0
    for nombre, da_cambio in MOTIVOS_BASE:
        if not MotivoSalida.objects.filter(nombre__iexact=nombre).exists():
            MotivoSalida.objects.create(nombre=nombre, da_cambio=da_cambio)
            creados += 1
    if creados:
        messages.success(request, f'Se agregaron {creados} motivo{"s" if creados != 1 else ""}.')
    else:
        messages.success(request, 'Los motivos de la HU ya estaban todos.')
    return redirect('motivos_salida')


@solo_superusuario
@require_POST
def editar_motivo_salida(request, id):
    motivo = get_object_or_404(MotivoSalida, id=id)
    formulario = MotivoForm(request.POST, instance=motivo)
    if formulario.is_valid():
        formulario.save()
        messages.success(request, f'Motivo «{motivo.nombre}» actualizado.')
    else:
        errores = ' '.join(e for lista in formulario.errors.values() for e in lista)
        messages.error(request, f'No se guardó el cambio: {errores}')
    return redirect('motivos_salida')


@solo_superusuario
@require_POST
def eliminar_motivo_salida(request, id):
    motivo = get_object_or_404(MotivoSalida, id=id)
    try:
        motivo.delete()
        messages.success(request, f'Motivo «{motivo.nombre}» eliminado.')
    except ProtectedError:
        messages.error(request, f'No se puede eliminar «{motivo.nombre}» porque ya hay salidas con ese motivo. '
                                'Puedes cambiarle el nombre.')
    return redirect('motivos_salida')