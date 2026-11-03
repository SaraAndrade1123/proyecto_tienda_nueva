import secrets
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import (login_required, permission_required, user_passes_test,)
from django.contrib.auth.models import Group, Permission
from django.core.mail import EmailMultiAlternatives
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from .models import User
from gestor_inventario.models import Perfil



# ==================================================
# INICIO
# ==================================================

def home(request):
    return redirect('lista_productos')


def es_superadmin(user):
    return user.is_authenticated and user.is_superuser


# ==================================================
# REGISTRO DE USUARIOS
# ==================================================

def registro(request):
    datos = ''
    errors = []

    if request.method == 'POST':
        document = request.POST.get('document', '').strip()
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        fecha_nacimiento = request.POST.get('fecha_nacimiento') or None
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        datos = request.POST

        if password1 != password2:
            errors.append('Las contraseñas no coinciden.')

        if User.objects.filter(username=username).exists():
            errors.append('El nombre de usuario ya existe.')

        if phone and User.objects.filter(phone=phone).exists():
            errors.append('El número de teléfono ya existe.')

        if email and User.objects.filter(email__iexact=email).exists():
            errors.append('El correo electrónico ya está registrado.')

        if not username:
            errors.append('El nombre de usuario es obligatorio.')

        if not email:
            errors.append('El correo electrónico es obligatorio.')

        if not password1:
            errors.append('La contraseña es obligatoria.')

        if not errors:
            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                fecha_nacimiento=fecha_nacimiento,
                phone=phone,
                email=email,
                password=password1,
            )

            login(request, user)
            return redirect('login')

    return render(request, 'usuario/registro.html', {
        'errors': errors,
        'datos': datos,
    })


# ==================================================
# RECUPERACIÓN DE CONTRASEÑA
# ==================================================

def recuperar_password(request):

    if request.method != 'POST':
        return render(
            request,
            'usuario/recuperar_password.html'
        )

    accion = request.POST.get('accion', 'solicitar')

    # ----------------------------------------------
    # SOLICITAR O REENVIAR CÓDIGO
    # ----------------------------------------------

    if accion in ['solicitar', 'reenviar']:

        if accion == 'solicitar':
            correo = request.POST.get('email', '').strip()

            usuario = User.objects.filter(
                email__iexact=correo
            ).first()

            if not usuario:
                return render(
                    request,
                    'usuario/recuperar_password.html',
                    {
                        'error': (
                            'No encontramos una cuenta con ese correo.'
                        )
                    }
                )

            request.session['recuperacion_email'] = usuario.email

        else:
            correo = request.session.get('recuperacion_email')

            if not correo:
                return render(
                    request,
                    'usuario/recuperar_password.html',
                    {
                        'error': (
                            'Ingresa tu correo para solicitar '
                            'un código nuevo.'
                        )
                    }
                )

            fecha_reenvio = request.session.get(
                'recuperacion_reenviar_despues'
            )

            if fecha_reenvio:
                momento_reenvio = datetime.fromisoformat(
                    fecha_reenvio
                )

                ahora = timezone.now()

                if ahora < momento_reenvio:
                    segundos = max(
                        1,
                        int(
                            (
                                momento_reenvio - ahora
                            ).total_seconds()
                        )
                    )

                    return render(
                        request,
                        'usuario/recuperar_password.html',
                        {
                            'codigo_enviado': True,
                            'error': (
                                'Debes esperar antes de reenviar '
                                'el código.'
                            ),
                            'reenviar_en': segundos,
                        }
                    )

            usuario = User.objects.filter(
                email__iexact=correo
            ).first()

            if not usuario:
                return render(
                    request,
                    'usuario/recuperar_password.html',
                    {
                        'error': 'No encontramos la cuenta.'
                    }
                )

        # Crear un código de seis dígitos.
        codigo = str(secrets.randbelow(900000) + 100000)

        ahora = timezone.now()

        # Guardar el código y su fecha de vencimiento.
        request.session['recuperacion_codigo'] = codigo

        request.session['recuperacion_expira'] = (
            ahora + timedelta(minutes=4)
        ).isoformat()

        # Esperar dos minutos antes de permitir otro envío.
        request.session['recuperacion_reenviar_despues'] = (
            ahora + timedelta(minutes=2)
        ).isoformat()

        # Preparar el correo.
        nombre = usuario.first_name or usuario.username

        mensaje_correo = (
            f"TIENDA NUEVA\n"
            f"Seguridad de tu cuenta\n\n"
            f"Hola, {nombre}.\n\n"
            f"Hemos recibido una solicitud para restablecer "
            f"la contraseña de tu cuenta.\n\n"
            f"Tu código de verificación es: {codigo}\n\n"
            f"Este código es válido durante 4 minutos. "
            f"Por seguridad, no lo compartas con nadie.\n\n"
            f"Si no solicitaste este cambio, ignora este "
            f"mensaje. Tu contraseña no se modificará "
            f"por esta solicitud.\n\n"
            f"Atentamente,\n"
            f"Equipo de Tienda Nueva\n\n"
            f"Mensaje automático. Por favor, no respondas "
            f"a este correo."
        )

        # Enviar el correo electrónico.
        send_mail(
            subject='Recuperación de contraseña | Tienda Nueva',
            message=mensaje_correo,
            from_email=None,
            recipient_list=[usuario.email],
            fail_silently=False,
        )

        return render(
            request,
            'usuario/recuperar_password.html',
            {
                'codigo_enviado': True,
                'reenviar_en': 120,
                'mensaje': (
                    'Te enviamos un código de recuperación. '
                    'Revisa tu correo electrónico.'
                ),
            }
        )

    # ----------------------------------------------
    # VERIFICAR CÓDIGO Y CAMBIAR CONTRASEÑA
    # ----------------------------------------------

    elif accion == 'verificar':

        codigo_ingresado = request.POST.get(
            'codigo', ''
        ).strip()

        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        codigo_guardado = request.session.get(
            'recuperacion_codigo'
        )

        fecha_expiracion = request.session.get(
            'recuperacion_expira'
        )

        correo = request.session.get(
            'recuperacion_email'
        )

        if not codigo_guardado or not fecha_expiracion or not correo:
            return render(
                request,
                'usuario/recuperar_password.html',
                {
                    'error': (
                        'Solicita un nuevo código de recuperación.'
                    )
                }
            )

        # Comprobar si el código venció.
        expiracion = datetime.fromisoformat(fecha_expiracion)

        if timezone.now() >= expiracion:

            request.session.pop('recuperacion_codigo', None)
            request.session.pop('recuperacion_expira', None)
            request.session.pop(
                'recuperacion_reenviar_despues',
                None
            )

            return render(
                request,
                'usuario/recuperar_password.html',
                {
                    'error': (
                        'El código venció. Solicita uno nuevo.'
                    )
                }
            )

        # Comprobar el código ingresado.
        if not secrets.compare_digest(
            codigo_ingresado,
            codigo_guardado
        ):
            return render(
                request,
                'usuario/recuperar_password.html',
                {
                    'codigo_enviado': True,
                    'error': (
                        'El código ingresado es incorrecto.'
                    ),
                }
            )

        # Validar la nueva contraseña.
        if len(password1) < 8:
            return render(
                request,
                'usuario/recuperar_password.html',
                {
                    'codigo_enviado': True,
                    'error': (
                        'La contraseña debe tener '
                        'al menos 8 caracteres.'
                    ),
                }
            )

        if password1 != password2:
            return render(
                request,
                'usuario/recuperar_password.html',
                {
                    'codigo_enviado': True,
                    'error': 'Las contraseñas no coinciden.',
                }
            )

        # Buscar al usuario.
        usuario = User.objects.filter(
            email__iexact=correo
        ).first()

        if not usuario:
            return render(
                request,
                'usuario/recuperar_password.html',
                {
                    'error': 'No encontramos la cuenta.'
                }
            )

        # Guardar la nueva contraseña.
        usuario.set_password(password1)
        usuario.save()

        # Eliminar los datos temporales de la sesión.
        claves = [
            'recuperacion_codigo',
            'recuperacion_expira',
            'recuperacion_email',
            'recuperacion_reenviar_despues',
        ]

        for clave in claves:
            request.session.pop(clave, None)

        return render(
            request,
            'usuario/recuperar_password.html',
            {
                'mensaje': (
                    '¡Contraseña actualizada! '
                    'Ya puedes iniciar sesión.'
                ),
                'recuperacion_completa': True,
            }
        )

    # Acción no reconocida.
    return render(
        request,
        'usuario/recuperar_password.html',
        {
            'error': 'La solicitud no es válida.'
        }
    )


# ==================================================
# INICIO DE SESIÓN
# ==================================================

def iniciar_sesion(request):

    if request.method == 'POST':

        correo = request.POST.get('email', '').strip()
        contraseña = request.POST.get('password', '')

        try:
            usuario = User.objects.get(
                email__iexact=correo
            )

        except User.DoesNotExist:
            return render(
                request,
                'login.html',
                {
                    'error': 'Correo o contraseña incorrectos'
                }
            )

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

        return render(
            request,
            'login.html',
            {
                'error': 'Correo o contraseña incorrectos'
            }
        )

    return render(request, 'login.html')


def cerrar_sesion(request):
    logout(request)
    return redirect('login')


# ==================================================
# EDITAR PERFIL
# ==================================================

@login_required
def editar_perfil(request):

    user = request.user

    perfil, _ = Perfil.objects.get_or_create(
        user=user
    )

    if request.method == 'POST':

        user.first_name = request.POST.get(
            'first_name', ''
        ).strip()

        user.last_name = request.POST.get(
            'last_name', ''
        ).strip()

        user.username = request.POST.get(
            'username', ''
        ).strip()

        user.phone = request.POST.get(
            'phone', ''
        ).strip()

        user.email = request.POST.get(
            'email', ''
        ).strip()

        fecha_nac = request.POST.get(
            'fecha_nacimiento', ''
        ).strip()

        user.fecha_nacimiento = fecha_nac or None

        errores = []

        if not user.first_name:
            errores.append('El nombre es obligatorio.')

        if not user.username:
            errores.append(
                'El nombre de usuario es obligatorio.'
            )

        if not user.email or '@' not in user.email:
            errores.append('El correo no es válido.')

        if User.objects.filter(
            username=user.username
        ).exclude(pk=user.pk).exists():
            errores.append(
                'Ese nombre de usuario ya está en uso.'
            )

        if User.objects.filter(
            email__iexact=user.email
        ).exclude(pk=user.pk).exists():
            errores.append(
                'Ese correo ya está registrado.'
            )

        if user.phone and User.objects.filter(
            phone=user.phone
        ).exclude(pk=user.pk).exists():
            errores.append(
                'Ese teléfono ya está registrado.'
            )

        if errores:

            for error in errores:
                messages.error(request, error)

        else:

            user.save()

            # Eliminar la foto de perfil.
            if request.POST.get('eliminar_foto'):

                if perfil.foto:
                    perfil.foto.delete(save=False)
                    perfil.foto = None
                    perfil.save()

                messages.success(
                    request,
                    'Foto de perfil eliminada.'
                )

                return redirect('editar_perfil')

            # Guardar una foto nueva.
            if 'foto' in request.FILES:
                perfil.foto = request.FILES['foto']
                perfil.save()

            messages.success(
                request,
                'Perfil actualizado correctamente.'
            )

            return redirect('editar_perfil')

    return render(
        request,
        'perfil/editar-perfil.html',
        {
            'user': user,
            'perfil': perfil,
        }
    )


# ==================================================
# ELIMINAR CUENTA
# ==================================================

@login_required
def eliminar_usuario(request):

    if request.method == 'POST':

        user = request.user

        logout(request)
        user.delete()

        return redirect('informacion_tienda')

    return redirect('editar_perfil')


# ==================================================
# GRUPOS
# ==================================================

@user_passes_test(es_superadmin)
def grupos(request):

    if request.method == 'POST':

        nombre = request.POST.get(
            'nombre', ''
        ).strip()

        if nombre and not Group.objects.filter(
            name=nombre
        ).exists():
            Group.objects.create(name=nombre)

        return redirect('grupos')

    grupos_lista = Group.objects.all()
    usuarios = User.objects.all()

    return render(
        request,
        'grupos.html',
        {
            'grupos': grupos_lista,
            'usuarios': usuarios,
        }
    )


@user_passes_test(es_superadmin)
def eliminar_grupo(request, id_grupo):

    if request.method == 'POST':

        grupo = get_object_or_404(
            Group,
            id=id_grupo
        )

        grupo.delete()

    return redirect('grupos')


def dar_miembros(grupo):
    return grupo.user_set.all()


def dar_no_miembros(grupo):

    miembros = dar_miembros(grupo)

    return User.objects.exclude(
        id__in=miembros.values_list(
            'id',
            flat=True
        )
    )


@user_passes_test(es_superadmin)
def editar_grupo(request, id_grupo):

    grupo = get_object_or_404(
        Group,
        id=id_grupo
    )

    if request.method == 'POST':

        nuevo_nombre = request.POST.get(
            'nombre', ''
        ).strip()

        if nuevo_nombre:
            grupo.name = nuevo_nombre
            grupo.save()

        return redirect('grupos')

    miembros = dar_miembros(grupo)
    no_miembros = dar_no_miembros(grupo)

    return render(
        request,
        'editar_grupo.html',
        {
            'grupo': grupo,
            'miembros': miembros,
            'no_miembros': no_miembros,
        }
    )


@user_passes_test(es_superadmin)
def agregar_usuario_grupo(request, id_grupo):

    grupo = get_object_or_404(
        Group,
        id=id_grupo
    )

    if request.method == 'POST':

        id_user = request.POST.get('id_usuario')

        if id_user:
            user = get_object_or_404(
                User,
                id=id_user
            )

            grupo.user_set.add(user)

        return redirect(
            'agregar_usuario_grupo',
            id_grupo=grupo.id
        )

    return redirect('grupos')


@user_passes_test(es_superadmin)
def eliminar_usuario_grupo(request, id_grupo):

    grupo = get_object_or_404(
        Group,
        id=id_grupo
    )

    if request.method == 'POST':

        id_user = request.POST.get('id_usuario')

        if id_user:
            user = get_object_or_404(
                User,
                id=id_user
            )

            grupo.user_set.remove(user)

        return redirect(
            'editar_grupo',
            id_grupo=grupo.id
        )

    return redirect(
        'editar_grupo',
        id_grupo=grupo.id
    )


# ==================================================
# PERMISOS
# ==================================================

@permission_required(
    'auth.add_permission',
    raise_exception=True
)
def permisos(request):

    permisos_lista = Permission.objects.all()
    grupos_lista = Group.objects.all()

    grupo_id = (
        request.POST.get('grupo')
        or request.GET.get('grupo')
    )

    if grupo_id:

        grupo = get_object_or_404(
            Group,
            id=grupo_id
        )

    else:
        grupo = grupos_lista.first()

    if request.method == 'POST':

        if not grupo:
            messages.error(
                request,
                'Primero debes crear un grupo.'
            )

            return redirect('grupos')

        permisos_ids = request.POST.getlist(
            'permisos'
        )

        grupo.permissions.set(permisos_ids)

        return redirect(
            f"{reverse('permisos')}?grupo={grupo.id}"
        )

    if grupo:

        permisos_grupo = set(
            grupo.permissions.values_list(
                'id',
                flat=True
            )
        )

    else:
        permisos_grupo = set()

    return render(
        request,
        'permisos.html',
        {
            'permisos': permisos_lista,
            'grupos': grupos_lista,
            'grupo': grupo,
            'permisos_grupo': permisos_grupo,
        }
    )
