from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

def iniciar_sesion(request):

    if request.method == 'POST':

        correo = request.POST.get('email')
        contraseña = request.POST.get('password')

        try:
            usuario = User.objects.get(email=correo)
        except User.DoesNotExist:
            return render(request, 'login.html', {
                'error': 'Correo o contraseña incorrectos'
            })

        usuario_autenticado = authenticate(
            request,
            username=usuario.username,
            password=contraseña
        )

        if usuario_autenticado is not None:
            login(request, usuario_autenticado)
            return redirect('home')

        return render(request, 'login.html', {
            'error': 'Correo o contraseña incorrectos'
        })

    return render(request, 'login.html')

'''
def home(request):

    if request.user.groups.filter(name='Cliente').exists():
        return render(request, 'home.html')

    return render(request, 'home.html', {
        'error': 'No tienes permisos para acceder a estas funciones.'
    })
'''