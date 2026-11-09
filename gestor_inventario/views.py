import json

from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.contrib import messages

from django.utils.dateparse import parse_date

from .models import (Proveedor, VisitaProveedor, ImagenCarrusel, ConsumoPersonal, DetalleConsumo)
from productos.models import Producto
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
                orden_actual = imagen_actual.orden
                orden_vecina = imagen_vecina.orden

                imagen_actual.orden = orden_vecina
                imagen_vecina.orden = orden_actual

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
@login_required
@user_passes_test(es_admin)
def ver_consumo(request):
    busqueda = request.GET.get('buscar', '').strip()
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    mes = request.GET.get('mes', '')

    ver_todos = request.GET.get('ver_todos') == '1'

    consumos = (
        ConsumoPersonal.objects.filter(activo=True).prefetch_related('detalles__producto')
    )

    if ver_todos:
        pass

    else:

        if mes:
            anio, mes_num = mes.split('-')
            consumos = consumos.filter(fecha__year=anio, fecha__month=mes_num)

        if fecha_inicio:
                consumos = consumos.filter(fecha__gte=fecha_inicio)

        if fecha_fin:
                consumos = consumos.filter(fecha__lte=fecha_fin)

        if not mes and not fecha_inicio and not fecha_fin and not busqueda:
            hoy = timezone.localdate()
            consumos = consumos.filter(fecha=hoy)

    if busqueda:
        consumos = consumos.filter(
            Q(persona__icontains=busqueda) | Q(detalles__producto__nombre__icontains=busqueda)
        ).distinct()
    
    consumos = consumos.order_by('-fecha', '-id')

    total_general = consumos.aggregate(total=Sum('total'))['total'] or 0
    total_registros = consumos.count()
    total_productos = (
        DetalleConsumo.objects.filter(consumo__in=consumos).aggregate(total=Sum('cantidad'))['total'] or 0
    )

    resumen_personas = (
        consumos.values('persona').annotate(total_consumido=Sum('total'), cantidad_registros=Count('id'),
        )
        .order_by('-total_consumido')
    )

    return render(request, 'consumo-lista.html',{
        'consumos' : consumos,
        'busqueda' : busqueda,
        'fecha_inicio' : fecha_inicio,
        'fecha_fin' : fecha_fin,
        'mes': mes,
        'total_general' : total_general,
        'total_registros' : total_registros,
        'total_productos' : total_productos,
        'resumen_personas' : resumen_personas,
        'ver_todos': ver_todos,
    })

@login_required
@user_passes_test(es_admin)
def agregar_consumo(request):
    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            persona_id = payload.get('persona_id')
            fecha = payload.get('fecha') or timezone.localdate().isoformat()
            items = payload.get('items', [])

            if not persona_id:
                return JsonResponse(
                    {'ok':False, 'error' : 'Debes seleccionar a una persona.'},
                    status=400
                )

            consumo = ConsumoPersonal.objects.create(
                persona=persona_id,
                fecha=fecha,
                total=0,
                activo=True
            )

            total = 0
            for item in items:
                producto_id = item.get('producto_id')
                cantidad = int(item.get('cantidad', 0))
                if cantidad <= 0:
                    continue

                try:
                    producto = Producto.objects.get(pk=producto_id)

                except Producto.DoesNotExist:
                    continue

                if producto.existencias < cantidad:
                    consumo.delete()
                    return JsonResponse({
                        'ok': False,
                        'error': f'No hay suficiente stock de {producto.nombre}. Quedan {producto.existencias} unidades.'
                    }, status=400)

                precio = int(producto.precio_unitario)
                subtotal = precio * cantidad
                
                producto.existencias -= cantidad
                producto.save(update_fields=['existencias'])

                DetalleConsumo.objects.create(
                    consumo=consumo,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=precio,
                    subtotal=subtotal
                )
                total += subtotal

            if total == 0 and not consumo.detalles.exists():
                consumo.delete()
                return JsonResponse(
                    {'ok' : False, 'error' : 'No se registró ningún producto válido'},
                    status=400
                )
            consumo.total = total
            consumo.save(update_fields=['total'])

            messages.success(
                request,
                f'Consumo registrado para {persona_id} con un total de ${total:,}.'
            )

            return JsonResponse({
                'ok': True,
                'consumo_id': consumo.id,
                'redirect': '/inventario/consumo/'
            })
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)
        except Exception as e:
            return JsonResponse({'ok': False, 'error': f'Error: {str(e)}'}, status=400)

    productos = Producto.objects.all().order_by('nombre')

    personas_choises = ConsumoPersonal.Personas.choices

    return render(request, 'consumo-agregar.html',{
        'productos': productos,
        'personas_choices': personas_choises,
    })

@login_required
@user_passes_test(es_admin)
def detalle_consumo(request, pk):
    consumo = get_object_or_404(
        ConsumoPersonal.objects,
        pk=pk,
        activo=True
    )
    detalles = consumo.detalles.select_related('producto').all()

    return render(request, 'consumo-detalle.html', {
        'consumo': consumo,
        'detalles': detalles,
    })

@login_required
@user_passes_test(es_admin)
@require_POST
def eliminar_consumo(request, pk):

    try:
        consumo = ConsumoPersonal.objects.get(pk=pk, activo=True)

        for detalle in consumo.detalles.all():
            producto = detalle.producto
            producto.existencias += detalle.cantidad
            producto.save(update_fields=['existencias'])

        consumo.activo = False
        consumo.save(update_fields=['activo'])

        messages.success(request, 'Consumo eliminado correctamente y stock devuleto al inventario.')

    except ConsumoPersonal.DoesNotExist:
        messages.warning(request, 'El consumo que intentas eliminar ya no existe o ya ha sido eliminado .')

    return redirect('ver_consumo')

# Auto completa los productos en el formulario
@login_required
@user_passes_test(es_admin)
def buscar_productos_api(request):

    q = request.GET.get('q','').strip()
    productos_qs = Producto.objects.all()

    if q:
        productos_qs = productos_qs.filter(nombre__icontains=q)

    productos = productos_qs.order_by('nombre')[:20]

    data = [{
        'id' : p.id,
        'nombre' : p.nombre,
        'precio' : float(p.precio_unitario),
        'existencias': p.existencias,
    } for p in productos ] 

    return JsonResponse({'productos': data})

@login_required
@user_passes_test(es_admin)
def buscar_sugerencias_api(request):
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'sugerencias': []})

    sugerencias = []

    for valor, texto in ConsumoPersonal.Personas.choices:
        if q.lower() in texto.lower():
            sugerencias.append({
                'tipo': 'persona',
                'valor': valor,
                'texto': f"{texto}"
            })

    productos = Producto.objects.filter(nombre__icontains=q)[:5]
    for p in productos:
        sugerencias.append({
            'tipo': 'producto',
            'valor': p.nombre,
            'texto': f"{p.nombre}"
        })    
    return JsonResponse({'sugerencias': sugerencias})