from functools import wraps

from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db.models import ProtectedError

from .models import Producto, Categoria
from .forms import ProductoForm, CategoriaForm


# ============================================================
# DECORADOR PARA FUNCIONES EXCLUSIVAS DEL SUPERUSUARIO
# ============================================================

def solo_superusuario(vista):

    @login_required
    @wraps(vista)
    def envoltura(request, *args, **kwargs):

        if not request.user.is_superuser:

            messages.error(
                request,
                'No tienes permisos para realizar esta acción.'
            )

            return redirect('lista_productos')

        return vista(request, *args, **kwargs)

    return envoltura


# ============================================================
# PRODUCTOS
# ============================================================

@login_required
def lista_productos(request):

    busqueda = request.GET.get(
        'buscar',
        ''
    ).strip()

    categoria_seleccionada = request.GET.get(
        'categoria',
        ''
    ).strip()

    productos = Producto.objects.select_related(
        'categoria'
    ).all()

    if busqueda:

        productos = productos.filter(
            Q(nombre__icontains=busqueda)
        )

    if categoria_seleccionada:

        productos = productos.filter(
            categoria_id=categoria_seleccionada
        )

    categorias = Categoria.objects.all()

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
                f'El producto {producto.nombre} '
                'no tiene existencias.'
            )

    return redirect('lista_productos')


@login_required
def detalle_producto(request, id):

    producto = Producto.objects.select_related(
        'categoria'
    ).filter(
        id=id
    ).first()

    if producto is None:

        return render(
            request,
            'productos/detalle_producto.html',
            {
                'producto': None
            },
            status=404
        )

    return render(
        request,
        'productos/detalle_producto.html',
        {
            'producto': producto
        }
    )


# ============================================================
# CATEGORÍAS
# ============================================================

@solo_superusuario
def lista_categorias(request):

    busqueda = request.GET.get(
        'buscar',
        ''
    ).strip()

    categorias = Categoria.objects.all()

    if busqueda:

        categorias = categorias.filter(
            nombre__icontains=busqueda
        )

    return render(
        request,
        'categorias/lista_categorias.html',
        {
            'categorias': categorias,
            'busqueda': busqueda,
        }
    )


@solo_superusuario
def crear_categoria(request):

    if request.method == 'POST':

        formulario = CategoriaForm(
            request.POST
        )

        if formulario.is_valid():

            formulario.save()

            messages.success(
                request,
                'Categoría creada correctamente.'
            )

            return redirect('lista_categorias')

    else:

        formulario = CategoriaForm()

    return render(
        request,
        'categorias/crear_categoria.html',
        {
            'formulario': formulario
        }
    )


@solo_superusuario
def editar_categoria(request, id):

    categoria = get_object_or_404(
        Categoria,
        id=id
    )

    if request.method == 'POST':

        formulario = CategoriaForm(
            request.POST,
            instance=categoria
        )

        if formulario.is_valid():

            formulario.save()

            messages.success(
                request,
                'Categoría actualizada correctamente.'
            )

            return redirect('lista_categorias')

    else:

        formulario = CategoriaForm(
            instance=categoria
        )

    return render(
        request,
        'categorias/editar_categoria.html',
        {
            'formulario': formulario,
            'categoria': categoria
        }
    )


@solo_superusuario
def eliminar_categoria(request, id):

    categoria = get_object_or_404(
        Categoria,
        id=id
    )

    if request.method == 'POST':

        try:

            categoria.delete()

            messages.success(
                request,
                'Categoría eliminada correctamente.'
            )

        except ProtectedError:

            messages.error(
                request,
                'No se puede eliminar esta categoría '
                'porque tiene productos asociados.'
            )

    return redirect('lista_categorias')

@login_required
def catalogo_productos(request):

    busqueda = request.GET.get('buscar', '').strip()
    categoria_seleccionada = request.GET.get('categoria', '').strip()

    productos = Producto.objects.select_related('categoria').all()

    if busqueda:
        productos = productos.filter(nombre__icontains=busqueda)

    if categoria_seleccionada:
        productos = productos.filter(categoria_id=categoria_seleccionada)

    return render(
        request,
        'productos/catalogo_productos.html',
        {
            'productos': productos,
            'busqueda': busqueda,
            'categoria_seleccionada': categoria_seleccionada,
            'categorias': Categoria.objects.all(),
        }
    )