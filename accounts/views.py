from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import User
from gestor_inventario.models import Perfil


def home(request):
    return redirect('lista_productos')


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
    user = request.user
    perfil, _ = Perfil.objects.get_or_create(user=user)

    if request.method == 'POST':
        # Recoger datos del POST
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name  = request.POST.get('last_name', '').strip()
        user.document   = request.POST.get('document', '').strip()
        user.username   = request.POST.get('username', '').strip()
        user.phone      = request.POST.get('phone', '').strip()
        user.email      = request.POST.get('email', '').strip()

        # Validaciones básicas
        errores = []
        if not user.first_name:
            errores.append('El nombre es obligatorio.')
        if not user.username:
            errores.append('El nombre de usuario es obligatorio.')
        if not user.email or '@' not in user.email:
            errores.append('El correo no es válido.')

        # Verificar que el username no esté usado por OTRO usuario
        if User.objects.filter(username=user.username).exclude(pk=user.pk).exists():
            errores.append('Ese nombre de usuario ya está en uso.')

        # Verificar que el documento no esté usado por OTRO usuario
        if User.objects.filter(document=user.document).exclude(pk=user.pk).exists():
            errores.append('Ese documento ya está registrado.')

        # Verificar que el email no esté usado por OTRO usuario
        if User.objects.filter(email=user.email).exclude(pk=user.pk).exists():
            errores.append('Ese correo ya está registrado.')

        # Verificar que el teléfono no esté usado por OTRO usuario
        if User.objects.filter(phone=user.phone).exclude(pk=user.pk).exists():
            errores.append('Ese teléfono ya está registrado.')

        if errores:
            for e in errores:
                messages.error(request, e)
        else:
            user.save()

            # Eliminar foto si el usuario presionó el botón
            if request.POST.get('eliminar_foto'):
                if perfil.foto:
                    perfil.foto.delete(save=False)  # borra el archivo físico del disco
                    perfil.foto = None
                    perfil.save()
                messages.success(request, 'Foto de perfil eliminada.')
                return redirect('editar_perfil')

            # Manejar la subida de una foto nueva
            if 'foto' in request.FILES:
                perfil.foto = request.FILES['foto']
                perfil.save()

            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('editar_perfil')

    return render(request, 'perfil/editar-perfil.html', {
        'user': user,
        'perfil': perfil,
    })


@login_required
def eliminar_usuario(request):
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        return redirect('informacion_tienda')
    return redirect('editar_perfil')
