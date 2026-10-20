from datetime import timedelta
from django.shortcuts import render , redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.utils import timezone

from .models import Proyecto, Tarea, Proveedor, VisitaProveedor
from accounts.views import es_superadmin as es_admin  # en este proyecto la función se llama es_superadmin
# hola prueba


@login_required

def informacion_tienda(request):
    return render(request, 'informacion.html')

def home(request):
    return render(request, 'home.html')

@login_required
def acerda_de(request):
    return render(request,'acerca-de.html')

@login_required
def mostrar_proyectos(request):
    proyectos = Proyecto.objects.all()
    return render(request, 'proyectos.html', {'proyectos': proyectos})

@login_required
def nuevos_registros(request):
    Proyecto.objects.create(
        nombre="Aplicación Bancaria", 
        descripcion="Aplicación web para gestionar cuentas bancarias", 
        duracion=1000
    )
    return HttpResponse('registro guardado')

@login_required
def ver_proyecto(request,id):
    proyecto = Proyecto.objects.get(id=id)
    return render(request, 'detalle-proyecto.html', {'proyecto': proyecto})

@login_required
def nuevo_proyecto(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        duracion = request.POST.get('duracion')
        imagen = request.FILES.get('imagen')
    
        if nombre and descripcion and duracion: 
            proyecto = Proyecto(
                nombre=nombre,
                descripcion=descripcion,
                duracion=duracion,
                imagen=imagen
            )
            proyecto.save()
    
            return redirect('proyectos')

    return render(request, 'nuevo-proyecto.html')

@login_required
def eliminar_proyecto(request, id):
    proyecto = Proyecto.objects.get(id=id)
    proyecto.delete()
    return redirect('proyectos')

@login_required
def editar_proyecto(request,id):   
    proyecto = Proyecto.objects.get(id=id)
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        duracion = request.POST.get('duracion')

        if nombre and descripcion and duracion:
            proyecto.nombre = nombre
            proyecto.descripcion = descripcion
            proyecto.duracion = int(duracion)
            proyecto.save()
            return redirect('ver_proyecto', id=proyecto.pk)
    
    return render(request,'editar-proyecto.html', {"proyecto":proyecto})

@login_required
def crear_tarea(request, proyecto_id):
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)

    if request.method == 'POST':
        titulo = request.POST.get('titulo').strip()
        prioridad = request.POST.get('prioridad')
        estado = request.POST.get('estado')

        if titulo:
            tarea = Tarea(
                titulo=titulo,
                prioridad=prioridad,
                estado=estado,
                proyecto=proyecto)
            tarea.save()

            return redirect('ver_proyecto', id=proyecto_id)
    
    datos = {
        'proyecto' : proyecto,
        'prioridad_choices': Tarea.PRIORIDAD_CHOICES,
        'estado_choices': Tarea.ESTADO_CHOICES
    }

    return render(request,'crear_tarea.html', datos)

#lo siguiente es un decorador, le da indicaciones a lo que esta debajo de el, ya sea metodo u otra cosa

@require_POST
def avanzar_estado_tarea(request, id):
    tarea = get_object_or_404(Tarea, id=id)

    if tarea.estado == 'PENDIENTE':
        tarea.estado = 'EN_PROGRESO'
        tarea.save()
    elif tarea.estado == 'EN_PROGRESO':
        tarea.estado = 'COMPLETADA'
        tarea.save()
    
    return redirect('ver_proyecto', id=tarea.proyecto.id)

def avanzar_rapido(request,id):
    tarea = get_object_or_404(Tarea, id=id)
    
    if tarea.estado != 'COMPLETADA':
        tarea.estado = 'COMPLETADA'
        tarea.save()
    
    return redirect('ver_proyecto', id=tarea.proyecto.id)

@require_POST
def eliminar_tarea(request,id):
    tarea = get_object_or_404(Tarea,id=id)
    id_proyecto = tarea.proyecto.id
    tarea.delete()
    return redirect('ver_proyecto',id=id_proyecto)


# =========================================================
# HU_008: CRUD_PROVEEDOR
# Criterio: "Solo el administrador puede agregar, buscar,
# eliminar, desactivar, editar al proveedor" -> @user_passes_test(es_admin)
# =========================================================

DIAS_AVISO_VISITA = 3  # con cuántos días de anticipación se muestra el aviso


@login_required
@user_passes_test(es_admin)
def mostrar_proveedores(request):
    query = request.GET.get('q', '').strip()
    mostrar_inactivos = request.GET.get('inactivos') == '1'

    proveedores = Proveedor.objects.all() if mostrar_inactivos else Proveedor.objects.filter(activo=True)

    if query:
        proveedores = proveedores.filter(
            Q(nombre__icontains=query) | Q(nit__icontains=query)
        )

    hoy = timezone.now().date()
    limite_aviso = hoy + timedelta(days=DIAS_AVISO_VISITA)

    datos = {
        'proveedores': proveedores,
        'query': query,
        'mostrar_inactivos': mostrar_inactivos,
        'hoy': hoy,
        'limite_aviso': limite_aviso,
    }
    return render(request, 'proveedores.html', datos)


@login_required
@user_passes_test(es_admin)
def nuevo_proveedor(request):
    error_nit = False
    datos_form = {}

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        nit = request.POST.get('nit', '').strip()
        telefono_contacto = request.POST.get('telefono_contacto', '').strip()
        correo = request.POST.get('correo', '').strip()
        fecha_visita = request.POST.get('fecha_visita')
        datos_form = request.POST

        # Criterio: "Si el NIT ya existe debe mostrar 'el usuario ya esta registrado' no se guarda"
        if Proveedor.objects.filter(nit=nit).exists():
            error_nit = True
        elif nombre and nit and telefono_contacto and correo:
            proveedor = Proveedor.objects.create(
                nombre=nombre,
                nit=nit,
                telefono_contacto=telefono_contacto,
                correo=correo,
            )
            if fecha_visita:
                VisitaProveedor.objects.create(proveedor=proveedor, fecha=fecha_visita)

            return redirect('proveedores')

    return render(request, 'nuevo-proveedor.html', {'error_nit': error_nit, 'datos': datos_form})


@login_required
@user_passes_test(es_admin)
def editar_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)
    error_nit = False

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        nit = request.POST.get('nit', '').strip()
        telefono_contacto = request.POST.get('telefono_contacto', '').strip()
        correo = request.POST.get('correo', '').strip()

        # El NIT ya existente en OTRO proveedor tampoco se debe guardar
        nit_duplicado = Proveedor.objects.filter(nit=nit).exclude(id=proveedor.id).exists()

        if nit_duplicado:
            error_nit = True
        elif nombre and nit and telefono_contacto and correo:
            proveedor.nombre = nombre
            proveedor.nit = nit
            proveedor.telefono_contacto = telefono_contacto
            proveedor.correo = correo
            proveedor.save()
            return redirect('proveedores')

    return render(request, 'editar-proveedor.html', {'proveedor': proveedor, 'error_nit': error_nit})


@require_POST
@login_required
@user_passes_test(es_admin)
def eliminar_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)
    proveedor.delete()
    return redirect('proveedores')


@require_POST
@login_required
@user_passes_test(es_admin)
def desactivar_proveedor(request, id):
    '''
    Criterio: "Poder desactivar un proveedor (no aparece en activos,
    pero debe permitir conservar su historial)"
    '''
    proveedor = get_object_or_404(Proveedor, id=id)
    proveedor.activo = False
    proveedor.save()
    return redirect('proveedores')


@require_POST
@login_required
@user_passes_test(es_admin)
def activar_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)
    proveedor.activo = True
    proveedor.save()
    return redirect('proveedores')


@login_required
@user_passes_test(es_admin)
def agregar_visita_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)

    if request.method == 'POST':
        fecha = request.POST.get('fecha')
        if fecha:
            VisitaProveedor.objects.create(proveedor=proveedor, fecha=fecha)

    return redirect('proveedores')
