from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import Producto
from .forms import ProductoForm


# ============================================================
# DECORADOR: SOLO SUPERUSUARIOS
# ============================================================

def solo_superusuario(vista):
    """
    - Si no ha iniciado sesión -> lo manda al login.
    - Si inició sesión pero NO es superusuario -> lo devuelve al
      catálogo con un mensaje de error.
    - Si es superusuario -> ejecuta la vista normalmente.
    """

    @login_required
    @wraps(vista)
    def envoltura(request, *args, **kwargs):

        if not request.user.is_superuser:
            messages.error(
                request,
                'No tienes permiso para realizar esta acción.'
            )
            return redirect('lista_productos')

        return vista(request, *args, **kwargs)

    return envoltura


# ============================================================
# CATÁLOGO (cualquier usuario con sesión iniciada)
# ============================================================

@login_required
def lista_productos(request):

    busqueda = request.GET.get('buscar', '').strip()
    categoria_seleccionada = request.GET.get('categoria', '').strip()

    productos = Producto.objects.all()

    if busqueda:
        productos = productos.filter(
            nombre__icontains=busqueda
        )

    if categoria_seleccionada:
        productos = productos.filter(
            categoria=categoria_seleccionada
        )

    categorias = Producto.CATEGORIAS_CHOICES

    return render(
        request,
        'productos/lista_productos.html',
        {
            'productos': productos,
            'busqueda': busqueda,
            'categoria_seleccionada': categoria_seleccionada,
            'categorias': categorias,
        }
    )


# ============================================================
# FUNCIONES SOLO PARA SUPERUSUARIO
# ============================================================

@solo_superusuario
def crear_producto(request):

    if request.method == 'POST':
        formulario = ProductoForm(
            request.POST,
            request.FILES
        )

        if formulario.is_valid():
            formulario.save()

            messages.success(
                request,
                'Producto creado correctamente.'
            )

            return redirect('lista_productos')

    else:
        formulario = ProductoForm()

    return render(
        request,
        'productos/crear_producto.html',
        {
            'formulario': formulario
        }
    )


@solo_superusuario
def editar_producto(request, id):

    producto = get_object_or_404(
        Producto,
        id=id
    )

    if request.method == 'POST':
        formulario = ProductoForm(
            request.POST,
            request.FILES,
            instance=producto
        )

        if formulario.is_valid():
            formulario.save()

            messages.success(
                request,
                'Producto actualizado correctamente.'
            )

            return redirect('lista_productos')

    else:
        formulario = ProductoForm(
            instance=producto
        )

    return render(
        request,
        'productos/editar_producto.html',
        {
            'formulario': formulario,
            'producto': producto
        }
    )


@solo_superusuario
def eliminar_producto(request, id):

    producto = get_object_or_404(
        Producto,
        id=id
    )

    if request.method == 'POST':
        producto.delete()

        messages.success(
            request,
            'Producto eliminado correctamente.'
        )

    return redirect('lista_productos')


@solo_superusuario
def aumentar_stock(request, id):

    producto = get_object_or_404(
        Producto,
        id=id
    )

    if request.method == 'POST':
        producto.existencias += 1
        producto.save()

        messages.success(
            request,
            f'Se aumentó el stock de {producto.nombre}.'
        )

    return redirect('lista_productos')


@solo_superusuario
def disminuir_stock(request, id):

    producto = get_object_or_404(
        Producto,
        id=id
    )

    if request.method == 'POST':
        if producto.existencias > 0:
            producto.existencias -= 1
            producto.save()

            messages.success(
                request,
                f'Se disminuyó el stock de {producto.nombre}.'
            )

        else:
            messages.warning(
                request,
                f'El producto {producto.nombre} no tiene existencias.'
            )

    return redirect('lista_productos')



@login_required
def detalle_producto(request, id):
    producto = Producto.objects.filter(id=id).first()

    if producto is None:
        return render(
            request,
            'productos/detalle_producto.html',
            {'producto': None},
            status=404
        )

    return render(
        request,
        'productos/detalle_producto.html',
        {'producto': producto}
    )