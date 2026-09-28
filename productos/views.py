from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .models import Producto
from .forms import ProductoForm


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