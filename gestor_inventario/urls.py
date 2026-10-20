from django.http import HttpResponse
from django.urls import path
from . import views

urlpatterns = [

    path('proveedores/',views.mostrar_proveedores,name='proveedores'),
    path('proveedores/nuevo/',views.nuevo_proveedor,name='nuevo_proveedor'),
    path('proveedores/<int:id>/editar/',views.editar_proveedor,name='editar_proveedor'),
    path('proveedores/<int:id>/eliminar/',views.eliminar_proveedor,name='eliminar_proveedor'),
    path('proveedores/<int:id>/desactivar/',views.desactivar_proveedor,name='desactivar_proveedor'),
    path('proveedores/<int:id>/activar/',views.activar_proveedor,name='activar_proveedor'),
    path('proveedores/<int:id>/visitas/nueva/',views.agregar_visita_proveedor,name='agregar_visita_proveedor'),

    path('', views.informacion_tienda, name='informacion_tienda'),
    path('consumo/', views.ver_consumo, name='ver_consumo'),
]
