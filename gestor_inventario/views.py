from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Max
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import Proveedor, VisitaProveedor, ImagenCarrusel
from accounts.views import es_superadmin as es_admin

@login_required
def home(request):
    return render(request, 'home.html')

@login_required
def acerda_de(request):
    return render(request, 'acerca-de.html')

#=====================================================================================================

DIAS_AVISO_VISITA = 3

@login_required
@user_passes_test(es_admin)
def mostrar_proveedores(request):
    query = request.GET.get('q', '').strip()
    mostrar_inactivos = request.GET.get('inactivos') == '1'

    proveedores = Proveedor.objects.all()

    if not mostrar_inactivos:
        proveedores = proveedores.filter(activo=True)

    if query:
        proveedores = proveedores.filter(
            Q(nombre_empresa__icontains=query) |
            Q(nit__icontains=query)
        )

    hoy = timezone.localdate()
    limite_aviso = hoy + timedelta(days=DIAS_AVISO_VISITA)

    datos = {
        'proveedores': proveedores,
        'query': query,
        'mostrar_inactivos': mostrar_inactivos,
        'hoy': hoy,
        'limite_aviso': limite_aviso,
    }

    return render(request, 'proveedores/lista.html', datos)


@login_required
@user_passes_test(es_admin)
def nuevo_proveedor(request):
    error_nit = False
    error_campos = False
    error_fecha = False
    datos_form = {}

    if request.method == 'POST':
        nombre_empresa = request.POST.get('nombre', '').strip()
        nit = request.POST.get('nit', '').strip()
        contacto_nombre = request.POST.get('telefono_contacto', '').strip() # Ojo: el formulario parece enviar esto en telefono_contacto
        telefono = request.POST.get('telefono', '').strip()
        email = request.POST.get('correo', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        fecha_visita_texto = request.POST.get('fecha_visita', '').strip()

        datos_form = request.POST

        # Todos los campos principales son obligatorios.
        if not all([nombre_empresa, nit, contacto_nombre, email]):
            error_campos = True

        # Comprobar que el NIT no esté registrado.
        elif Proveedor.objects.filter(nit=nit).exists():
            error_nit = True

        else:
            fecha_visita = None
            if fecha_visita_texto:
                fecha_visita = parse_date(fecha_visita_texto)
                if fecha_visita is None:
                    error_fecha = True

            if not error_fecha:
                proveedor = Proveedor.objects.create(
                    nombre_empresa=nombre_empresa,
                    nit=nit,
                    contacto_nombre=contacto_nombre,
                    telefono=telefono,
                    email=email,
                    direccion=direccion or None,
                )

                if fecha_visita:
                    VisitaProveedor.objects.create(
                        proveedor=proveedor,
                        fecha=fecha_visita
                    )

                return redirect('proveedores')

    return render(
        request,
        'proveedores/registro_y_edicion.html',
        {
            'error_nit': error_nit,
            'error_campos': error_campos,
            'error_fecha': error_fecha,
            'datos': datos_form,
        }
    )


@login_required
@user_passes_test(es_admin)
def editar_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)

    error_nit = False
    error_campos = False

    if request.method == 'POST':
        nombre_empresa = request.POST.get('nombre', '').strip()
        nit = request.POST.get('nit', '').strip()
        contacto_nombre = request.POST.get('telefono_contacto', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        email = request.POST.get('correo', '').strip()
        direccion = request.POST.get('direccion', '').strip()

        if not all([nombre_empresa, nit, contacto_nombre, email]):
            error_campos = True

        elif Proveedor.objects.filter(nit=nit).exclude(id=proveedor.id).exists():
            error_nit = True

        else:
            proveedor.nombre_empresa = nombre_empresa
            proveedor.nit = nit
            proveedor.contacto_nombre = contacto_nombre
            proveedor.telefono = telefono
            proveedor.email = email
            proveedor.direccion = direccion or None
            proveedor.save()

            return redirect('proveedores')

    return render(
        request,
        'proveedores/registro_y_edicion.html',
        {
            'proveedor': proveedor,
            'error_nit': error_nit,
            'error_campos': error_campos,
        }
    )


@login_required
@user_passes_test(es_admin)
@require_POST
def eliminar_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)
    proveedor.delete()
    return redirect('proveedores')


@login_required
@user_passes_test(es_admin)
@require_POST
def desactivar_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)
    proveedor.activo = False
    proveedor.save(update_fields=['activo'])
    return redirect('proveedores')


@login_required
@user_passes_test(es_admin)
@require_POST
def activar_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)
    proveedor.activo = True
    proveedor.save(update_fields=['activo'])
    return redirect('proveedores')


@login_required
@user_passes_test(es_admin)
@require_POST
def agregar_visita_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)
    fecha_texto = request.POST.get('fecha', '').strip()
    fecha = parse_date(fecha_texto)

    if fecha:
        VisitaProveedor.objects.create(
            proveedor=proveedor,
            fecha=fecha
        )
    return redirect('proveedores')

#=====================================================================================================

def ordenar_imagenes():
    # Función auxiliar para reordenar
    imagenes = list(ImagenCarrusel.objects.order_by('orden', 'fecha_creacion', 'id'))
    for posicion, img in enumerate(imagenes, start=1):
        if img.orden != posicion:
            img.orden = posicion
            img.save(update_fields=['orden'])

@login_required
def informacion_tienda(request):
    if request.method == 'POST':
        # Asumo que es_administrador está definida en algún lado, si no, usa es_admin
        # if not es_administrador(request.user):
        #     messages.error(request, 'No tienes permisos para modificar el carrusel.')
        #     return redirect('informacion_tienda')

        accion = request.POST.get('accion')

        if accion == 'agregar':
            archivos = request.FILES.getlist('imagenes')
            if not archivos:
                messages.warning(request, 'Selecciona al menos una imagen.')
                return redirect('informacion_tienda')

            ultimo_orden = ImagenCarrusel.objects.aggregate(mayor=Max('orden'))['mayor'] or 0
            for archivo in archivos:
                ultimo_orden += 1
                ImagenCarrusel.objects.create(imagen=archivo, orden=ultimo_orden)
            messages.success(request, 'Las imágenes se agregaron correctamente.')

        elif accion == 'eliminar':
            imagen_id = request.POST.get('imagen_id')
            try:
                imagen = ImagenCarrusel.objects.get(pk=imagen_id)
                imagen.imagen.delete(save=False)
                imagen.delete()
                ordenar_imagenes()
                messages.success(request, 'La imagen se eliminó correctamente.')
            except (ImagenCarrusel.DoesNotExist, ValueError, TypeError):
                messages.error(request, 'No se encontró la imagen seleccionada.')

        elif accion == 'mover':
            imagen_id = request.POST.get('imagen_id')
            direccion = request.POST.get('direccion')

            if direccion not in ('izquierda', 'derecha'):
                messages.error(request, 'Dirección no válida.')
                return redirect('informacion_tienda')

            with transaction.atomic():
                imagenes = list(ImagenCarrusel.objects.select_for_update().order_by('orden', 'fecha_creacion', 'id'))
                indice = next((i for i, img in enumerate(imagenes) if str(img.pk) == str(imagen_id)), None)

                if indice is not None:
                    nuevo_indice = indice - 1 if direccion == 'izquierda' else indice + 1
                    if 0 <= nuevo_indice < len(imagenes):
                        imagenes[indice], imagenes[nuevo_indice] = imagenes[nuevo_indice], imagenes[indice]
                        for posicion, img in enumerate(imagenes, start=1):
                            if img.orden != posicion:
                                img.orden = posicion
                                img.save(update_fields=['orden'])

        return redirect('informacion_tienda')

    imagenes = ImagenCarrusel.objects.all()
    return render(request, 'informacion.html', {'imagenes': imagenes})


def ver_consumo(request):
    return render(request, 'consumo.html')