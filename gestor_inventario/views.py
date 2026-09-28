from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Producto

def informacion_tienda(request):
    return render(request, 'informacion.html' )
