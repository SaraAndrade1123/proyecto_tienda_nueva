from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.db.models import Max
from .models import ImagenCarrusel

def es_administrador(user):
    return user.is_authenticated and user.is_staff

def ordenar_imagenes():
    imagenes = ImagenCarrusel.objects.order_by('orden', 'fecha_creacion', 'id')
    for posicion, imagen in enumerate(imagenes, start=1):
        if imagen.orden != posicion:
            imagen.orden = posicion
            imagen.save(update_fields=['orden'])

def informacion_tienda(request):
    if request.method == 'POST':
        if not es_administrador(request.user):
            messages.error(request, 'No tienes permisos para modificar el carrusel.')
            return redirect('informacion_tienda')

        accion = request.POST.get('accion')

        if accion == 'agregar':
            # Aquí recibimos las imágenes directamente, sin forms.py
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
    pass
