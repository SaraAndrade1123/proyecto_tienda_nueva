import secrets
from datetime import timedelta
from django.core.mail import send_mail
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.contrib import messages
from .models import User
from gestor_inventario.models import Perfil
from django.contrib.auth.models import Group, Permission
from django.urls import reverse
from django.contrib.auth import get_user_model

def home(request):
    return redirect('lista_productos')

def es_superadmin(user):
    return user.is_authenticated and user.is_superuser

def registro(request):
    datos = ''
    errors = []

    if request.method == "POST":
        document = request.POST.get('document', '').strip()
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        fecha_nacimiento = request.POST.get('fecha_nacimiento') or None
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

    if request.method == "POST":
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        fecha_nacimiento = request.POST.get('fecha_nacimiento') or None
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        datos = request.POST

        if password1 != password2:
            errors.append('Las contraseñas no coinciden')

        if User.objects.filter(username=username).exists():
            errors.append('El nombre de usuario ya existe')

        if phone and User.objects.filter(phone=phone).exists():
            errors.append('El número de teléfono ya existe')

        if email and User.objects.filter(email=email).exists():
            errors.append('El correo electrónico ya está registrado')

        if not errors:
            user = User.objects.create_user(
                username=username,
                fecha_nacimiento=fecha_nacimiento,
                phone=phone,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name
            )
            login(request, user)
            return redirect('login')

    return render(request, 'usuario/registro.html', {'errors': errors, 'datos': datos})


def recuperar_password(request):
    if request.method == 'POST':
        accion = request.POST.get('accion', 'solicitar')

        if accion in ['solicitar', 'reenviar']:
            if accion == 'solicitar':
                correo = request.POST.get('email', '').strip()
                usuario = User.objects.filter(email__iexact=correo).first()

                if not usuario:
                    return render(request, 'usuario/recuperar_password.html', {
                        'error': 'No encontramos una cuenta con ese correo.'
                    })

                request.session['recuperacion_email'] = usuario.email

            else:
                correo = request.session.get('recuperacion_email')

                if not correo:
                    return render(request, 'usuario/recuperar_password.html', {
                        'error': 'Ingresa tu correo para solicitar un código nuevo.'
                    })

                fecha_reenvio = request.session.get(
                    'recuperacion_reenviar_despues'
                )

                if fecha_reenvio:
                    momento_reenvio = timezone.datetime.fromisoformat(
                        fecha_reenvio
                    )

                    if timezone.now() < momento_reenvio:
                        segundos = max(1, int(
                            (momento_reenvio - timezone.now()).total_seconds()
                        ))

                        return render(request, 'usuario/recuperar_password.html', {
                            'codigo_enviado': True,
                            'error': 'Todavía debes esperar para reenviar el código.',
                            'reenviar_en': segundos,
                        })

                usuario = User.objects.filter(email__iexact=correo).first()

                if not usuario:
                    return render(request, 'usuario/recuperar_password.html', {
                        'error': 'No encontramos la cuenta.'
                    })

            codigo = str(secrets.randbelow(900000) + 100000)
            ahora = timezone.now()

            request.session['recuperacion_codigo'] = codigo
            request.session['recuperacion_expira'] = (
                ahora + timedelta(minutes=4)
            ).isoformat()
            request.session['recuperacion_reenviar_despues'] = (
                ahora + timedelta(minutes=2)
            ).isoformat()

            send_mail(
                subject='Código de recuperación - Tienda Nueva',
                message=(
                    f'Hola {usuario.first_name or usuario.username}.\n\n'
                    f'Tu código de recuperación es: {codigo}\n\n'
                    'Este código vence en 4 minutos. '
                    'Si no solicitaste este cambio, ignora este mensaje.'
                ),
                from_email=None,
                recipient_list=[usuario.email],
                fail_silently=False,
            )

            return render(request, 'usuario/recuperar_password.html', {
                'codigo_enviado': True,
                'reenviar_en': 300,
                'mensaje': 'Te enviamos un código de recuperación. Revisa tu correo.',
            })

        elif accion == 'verificar':
            codigo_ingresado = request.POST.get('codigo', '').strip()
            password1 = request.POST.get('password1', '')
            password2 = request.POST.get('password2', '')

            codigo_guardado = request.session.get('recuperacion_codigo')
            fecha_expiracion = request.session.get('recuperacion_expira')
            correo = request.session.get('recuperacion_email')

            if not codigo_guardado or not fecha_expiracion or not correo:
                return render(request, 'usuario/recuperar_password.html', {
                    'error': 'Solicita un nuevo código de recuperación.'
                })

            if timezone.now() >= timezone.datetime.fromisoformat(fecha_expiracion):
                request.session.pop('recuperacion_codigo', None)
                request.session.pop('recuperacion_expira', None)
                request.session.pop('recuperacion_reenviar_despues', None)

                return render(request, 'usuario/recuperar_password.html', {
                    'error': 'El código venció. Solicita uno nuevo.'
                })

            if not secrets.compare_digest(codigo_ingresado, codigo_guardado):
                return render(request, 'usuario/recuperar_password.html', {
                    'codigo_enviado': True,
                    'error': 'El código ingresado es incorrecto.',
                })

            if len(password1) < 8:
                return render(request, 'usuario/recuperar_password.html', {
                    'codigo_enviado': True,
                    'error': 'La contraseña debe tener al menos 8 caracteres.',
                })

            if password1 != password2:
                return render(request, 'usuario/recuperar_password.html', {
                    'codigo_enviado': True,
                    'error': 'Las contraseñas no coinciden.',
                })

            usuario = User.objects.filter(email__iexact=correo).first()

            if not usuario:
                return render(request, 'usuario/recuperar_password.html', {
                    'error': 'No encontramos la cuenta.'
                })

            usuario.set_password(password1)
            usuario.save()

            for clave in [
                'recuperacion_codigo',
                'recuperacion_expira',
                'recuperacion_email',
                'recuperacion_reenviar_despues',
            ]:
                request.session.pop(clave, None)

            return render(request, 'usuario/recuperar_password.html', {
                'mensaje': '¡Contraseña actualizada! Ya puedes iniciar sesión.',
                'recuperacion_completa': True,
            })

    return render(request, 'usuario/recuperar_password.html')


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
        user.first_name       = request.POST.get('first_name', '').strip()
        user.last_name        = request.POST.get('last_name', '').strip()
        user.username         = request.POST.get('username', '').strip()
        user.phone            = request.POST.get('phone', '').strip()
        user.email            = request.POST.get('email', '').strip()
        fecha_nac             = request.POST.get('fecha_nacimiento', '').strip()
        user.fecha_nacimiento = fecha_nac if fecha_nac else None

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

        # Verificar que el email no esté usado por OTRO usuario
        if User.objects.filter(email=user.email).exclude(pk=user.pk).exists():
            errores.append('Ese correo ya está registrado.')

        # Verificar que el teléfono no esté usado por OTRO usuario
        if user.phone and User.objects.filter(phone=user.phone).exclude(pk=user.pk).exists():
            errores.append('Ese teléfono ya está registrado.')

        if errores:
            for e in errores:
                messages.error(request, e)
        else:
            user.save()

            # Eliminar foto si el usuario presionó el botón
            if request.POST.get('eliminar_foto'):
                if perfil.foto:
                    perfil.foto.delete(save=False)
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

@user_passes_test(es_superadmin)
def grupos(request):
    if request.method == "POST":
        nombre = request.POST.get('nombre', '').strip()
        if nombre and not Group.objects.filter(name=nombre).exists():
            Group.objects.create(name=nombre)
        return redirect('grupos')

    grupos = Group.objects.all()
    usuarios = User.objects.all()

    return render(request, 'grupos.html', {
        'grupos': grupos,
        'usuarios': usuarios
    })

@user_passes_test(es_superadmin)
def eliminar_grupo(request, id_grupo):
    if request.method == "POST":
        grupo = get_object_or_404 (Group, id=id_grupo)
        grupo.delete()
    return redirect('grupos')

def dar_miembros(grupo):
    return grupo.user_set.all()

def dar_no_miembros(grupo):
    miembros = dar_miembros(grupo)
    return User.objects.exclude(id__in=miembros.values_list('id', flat=True))


@user_passes_test(es_superadmin)
def editar_grupo(request, id_grupo):
    grupo = get_object_or_404(Group, id=id_grupo)

    if request.method == "POST":
        nuevo_nombre = request.POST.get('nombre', '').strip()

        if nuevo_nombre:
            grupo.name = nuevo_nombre
            grupo.save()


        return redirect('grupos')

    miembros = dar_miembros(grupo)
    no_miembros = dar_no_miembros(grupo)

    return render(request, 'editar_grupo.html', {
        'grupo': grupo,
        'miembros': miembros,
        'no_miembros': no_miembros,
    })

@user_passes_test(es_superadmin)
def agregar_usuario_grupo(request, id_grupo):
    grupo = get_object_or_404(Group, id=id_grupo)
    if request.method == "POST":
        id_user = request.POST.get('id_usuario')
        if id_user:
            user = get_object_or_404(User, id=id_user)
            grupo.user_set.add(user)

        return redirect('agregar_usuario_grupo', id_grupo=grupo.id)
    return redirect('grupos')

@user_passes_test(es_superadmin)
def eliminar_usuario_grupo(request, id_grupo):
    grupo = get_object_or_404(Group, id=id_grupo)
    if request.method == "POST":
        id_user = request.POST.get('id_usuario')
        if id_user:
            user = get_object_or_404(User, id=id_user)
            grupo.user_set.remove(user)

        return redirect('editar_grupo', id_grupo=grupo.id)
    
    return render(request, 'editar_grupo', id_grupo=grupo.id)

@permission_required('auth.add_permission', raise_exception=True)
def permisos(request):
    permisos = Permission.objects.all()
    grupos = Group.objects.all()

    if request.POST.get('grupo'):
        grupo_id = request.POST.get('grupo')
    else:
        grupo_id = request.GET.get('grupo')

    if grupo_id:
        grupo = get_object_or_404(Group, id=grupo_id)
    else:
        grupo = grupos.first()

    if request.method == "POST":
        permisos_ids = request.POST.getlist('permisos')
        grupo.permissions.set(permisos_ids)
        return redirect(f"{reverse('permisos')}?grupo={grupo.id}")

    if grupo:
        permisos_grupo = set(grupo.permissions.values_list('id', flat=True))
    else:
        permisos_grupo = set()

    return render(request, 'permisos.html', {
        'permisos': permisos,
        'grupos': grupos,
        'grupo': grupo,
        'permisos_grupo': permisos_grupo
    })