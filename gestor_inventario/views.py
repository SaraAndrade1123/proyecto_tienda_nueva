from django.shortcuts import render

def informacion_tienda(request):
    return render(request, 'informacion.html' )