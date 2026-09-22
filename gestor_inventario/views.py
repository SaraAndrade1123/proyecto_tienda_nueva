from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Producto

def informacion_tienda(request):
    return render(request, 'informacion.html' )

@login_required
def catalogo(request):
    
    if not request.user.groups.filter(name='Cliente').exists():
        return render(request, 'catalogo.html', {
            'productos': [],
            'error': 'No tienes permiso para acceder al catálogo.'
        })
        
    productos = Producto.objects.all()
    busqueda = request.GET.get('buscar')

    if busqueda:
        productos = productos.filter(nombre__icontains=busqueda)

    return render(request, 'catalogo.html', {
        'productos': productos
    })
