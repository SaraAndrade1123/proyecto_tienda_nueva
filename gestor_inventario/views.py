from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.contrib import messages

from .models import Proveedor, VisitaProveedor, ImagenCarrusel
from accounts.views import es_superadmin as es_admin

# =========================================================

@login_required
def informacion_tienda(request):
    imagenes = ImagenCarrusel.objects.all()

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'agregar':
            imagenes_subidas = request.FILES.getlist('imagenes')

            if imagenes_subidas:
                for img in imagenes_subidas:
                    ImagenCarrusel.objects.create(imagen=img)

                messages.success(request, 'Imagenes subidas correctamente.')
            else:
                messages.error(request, 'No se selecciono ninguna imagen.')

            return redirect('informacion_tienda')

        elif accion == 'eliminar':
            imagen_id = request.POST.get('imagen_id')
            imagen = get_object_or_404(ImagenCarrusel, id=imagen_id)
            imagen.delete()

            messages.success(request, 'Imagen eliminada correctamente')

            return redirect('informacion_tienda')

        elif accion == 'mover':
            imagen_id = request.POST.get('imagen_id')
            direccion = request.POST.get('direccion')
            imagen_actual = get_object_or_404(ImagenCarrusel, id=imagen_id)

            if direccion == 'izquierda':
                imagen_vecina = ImagenCarrusel.objects.filter(orden__lt=imagen_actual.orden).order_by('-orden').first()
            else:
                imagen_vecina = ImagenCarrusel.objects.filter(orden__gt=imagen_actual.orden).order_by('orden').first()

            if imagen_vecina:
                imagen_actual.orden, imagen_vecina.orden = imagen_vecina.orden, imagen_actual.orden

                imagen_actual.save()
                imagen_vecina.save()

            return redirect('informacion_tienda')

    # Diccionario
    context = {
        'imagenes': imagenes
    }
    return render(request, 'informacion.html', context)



def home(request):
    return render(request, 'home.html')

@login_required
def acerda_de(request):
    return render(request, 'acerca-de.html')

# =========================================================

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
        contacto_nombre = request.POST.get('telefono_contacto', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        email = request.POST.get('correo', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        fecha_visita_texto = request.POST.get('fecha_visita', '').strip()

        datos_form = request.POST

        if not all([nombre_empresa, nit, contacto_nombre, email]):
            error_campos = True

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

#=================================================

def ver_consumo(request):
    return render(request, 'consumo.html')

def agregar_consumo(request):
    pass