import logging
from functools import wraps

from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError, transaction
from django.db.models import F, Q
from django.db.models import ProtectedError
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Producto, Categoria, Transaccion
from .forms import ProductoForm, CategoriaForm

logger = logging.getLogger(__name__)


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

def informacion_tienda(request):
      return render(request, 'informacion.html')


# ====================================================================
#  VENTAS  ->  TRANSACCIONES
#  Cada venta crea una fila nueva en el modelo Transaccion (base de datos
#  compartida) y descuenta el stock del producto. La fila guarda el nombre
#  y el precio de ESE momento y después no se puede modificar (ver models.py).
# ====================================================================

def _pesos(valor):
    """11700 -> '$11.700'   |   3801.5 -> '$3.801,50'"""
    texto = f'{valor:,.2f}'.replace(',', '#').replace('.', ',').replace('#', '.')
    if texto.endswith(',00'):
        texto = texto[:-3]
    return f'${texto}'


def _responder_venta(request, es_ajax, ok, mensaje, **extra):
    """Si la petición viene del campo de venta (fetch) responde JSON; si no, deja un mensaje y vuelve a la lista."""
    if es_ajax:
        return JsonResponse({'ok': ok, 'mensaje': mensaje, **extra}, status=200 if ok else 400)

    if ok:
        messages.success(request, mensaje)
    else:
        messages.error(request, mensaje)

    return redirect('lista_productos')


@solo_superusuario
@require_POST
def vender_producto(request, id):

    producto = get_object_or_404(Producto, id=id)

    es_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    # 1) Leer y validar la cantidad (un entero de 1 en adelante)
    try:
        cantidad = int(request.POST.get('cantidad', '').strip())
    except ValueError:
        cantidad = 0

    if cantidad < 1:
        return _responder_venta(
            request, es_ajax, False,
            'Escribe cuántas unidades vendiste (un número entero mayor que 0).',
            existencias=producto.existencias
        )

    # 2) Todo o nada: si algo falla, no se descuenta stock ni se guarda la transacción
    try:
        with transaction.atomic():

            # Descuenta solo si alcanza el stock. Es UNA sola instrucción SQL, así que
            # si dos personas venden a la vez nunca se vende más de lo que hay.
            filas = Producto.objects.filter(
                pk=producto.pk,
                existencias__gte=cantidad
            ).update(existencias=F('existencias') - cantidad)

            if filas == 0:
                producto.refresh_from_db()
                return _responder_venta(
                    request, es_ajax, False,
                    f'No alcanza: de {producto.nombre} solo quedan {producto.existencias}.',
                    existencias=producto.existencias
                )

            # La fila del producto ya quedó bloqueada por esta transacción, así que lo que
            # leemos ahora (precio, nombre, existencias) es lo vigente y nadie lo cambia
            # hasta que terminemos: esa es la «foto» que se guarda en la transacción.
            producto.refresh_from_db()

            # 3) Guardar el registro. La fecha y hora exactas se ponen solas y el total
            #    (precio × cantidad) lo calcula Transaccion.save().
            transaccion = Transaccion.objects.create(
                nom_producto=producto.nombre,
                precio=producto.precio_unitario,
                cantidad=cantidad
            )

    except DatabaseError:
        # Pasa, por ejemplo, si todavía no se ejecutó «python manage.py migrate» (la tabla
        # no existe). Al salir del «with» la base ya deshizo el descuento de stock.
        # El error completo queda en la terminal del servidor.
        logger.exception('No se pudo registrar la transacción de %s', producto.nombre)
        producto.refresh_from_db()
        return _responder_venta(
            request, es_ajax, False,
            'No se pudo registrar la venta y no se descontó nada. '
            'Si es la primera vez, falta ejecutar «python manage.py migrate».',
            existencias=producto.existencias
        )

    # 4) Responder
    return _responder_venta(
        request, es_ajax, True,
        f'Vendiste {cantidad} de {producto.nombre} por {_pesos(transaccion.total)}. '
        f'Quedan {producto.existencias}.',
        existencias=producto.existencias,
        producto_id=producto.id
    )