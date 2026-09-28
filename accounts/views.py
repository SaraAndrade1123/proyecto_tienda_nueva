from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import Group, Permission

from .models import User
from django.contrib.auth.decorators import user_passes_test, permission_required
from django.urls import reverse

from django.contrib.auth.decorators import login_required

def home(request):
    return render(request, 'home.html')

def registro(request):
    datos = ''
    errors = []

    if request.method == "POST":
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        document = request.POST.get('document')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        

        datos = request.POST

        print(username)
        # Validacion basica
        if password1 != password2:
            errors.append('Las contraseñas no coinciden')

        if User.objects.filter(username=username).exists():
            errors.append('El nombre de usuario ya existe')

        if User.objects.filter(document=document).exists():
            errors.append('El documento ya esta registrado')

        if User.objects.filter(phone=phone).exists():
            errors.append('El numero de telefono ya existe')

        if User.objects.filter(email=email).exists():
            errors.append('El correo electronico ya esta registrado')



        if not errors:
            # Create _user hashea la contraseña automaticamente
            user = User.objects.create_user(
                username=username,
                document=document,
                phone=phone,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name
            )
            login(request, user)
            return redirect('login')

            
    return render(request, 'usuario/registro.html', {'errors': errors, 'datos': datos})

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
            if usuario_autenticado.is_staff:
                return redirect('lista_productos')
            return redirect('informacion_tienda')

        return render(request, 'login.html', {
            'error': 'Correo o contraseña incorrectos'
        })

    return render(request, 'login.html')

def cerrar_sesion(request):
    logout(request)
    return redirect('login')

@login_required
def editar_perfil(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone = request.POST.get('phone', getattr(user, 'phone', ''))
        user.save()

        # Actualizar foto si el modelo Perfil la maneja
        if hasattr(user, 'perfil'):
            foto = request.FILES.get('foto')
            if foto:
                user.perfil.foto = foto
                user.perfil.save()

        return redirect('informacion')

    return render(request, 'perfil/editar-perfil.html')
    
