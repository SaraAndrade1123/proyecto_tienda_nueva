from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Proveedor
from .forms import ProveedorForm
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q


def lista_proveedores(request):
    proveedores = Proveedor.objects.all()

    busqueda = request.GET.get('buscar', '')

    if busqueda:
        proveedores = proveedores.filter(
            Q(nombre_empresa__icontains=busqueda) |
            Q(nit__icontains=busqueda) |
            Q(contacto_nombre__icontains=busqueda) |
            Q(email__icontains=busqueda)
        )

    hoy = timezone.localdate()
    manana = hoy + timedelta(days=1)
    limite = hoy + timedelta(days=7)

    filtro = request.GET.get('filtro', 'todos')

    if filtro == 'activos':
        proveedores = proveedores.filter(activo=True)

    elif filtro == 'inactivos':
        proveedores = proveedores.filter(activo=False)

    elif filtro == 'urgentes':
        proveedores = proveedores.filter(
            activo=True,
            proxima_visita=manana
        )

    visitas_proximas = proveedores.filter(
        activo=True,
        proxima_visita__gte=hoy,
        proxima_visita__lte=limite
    )

    return render(request, 'proveedores/lista.html', {
        'proveedores': proveedores,
        'visitas_proximas': visitas_proximas,
        'busqueda': busqueda,
        'filtro': filtro,
    })

def crear_proveedor(request):
    if request.method == 'POST':
        form = ProveedorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "¡Proveedor registrado exitosamente!")
            return redirect('lista_proveedores')
    else:
        form = ProveedorForm()
    return render(request, 'proveedores/registro_y_edicion.html', {'form': form, 'titulo': 'Registrar Proveedor'})

def editar_proveedor(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    if request.method == 'POST':
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            form.save()
            messages.success(request, "¡Datos del proveedor actualizados correctamente!")
            return redirect('lista_proveedores')
    else:
        form = ProveedorForm(instance=proveedor)
    
    return render(request, 'proveedores/registro_y_edicion.html', {'form': form, 'titulo': 'Editar Proveedor'})