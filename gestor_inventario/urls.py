from django.http import HttpResponse
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home,name='home'),

    path('proveedores/',views.mostrar_proveedores,name='proveedores'),
    path('proveedores/nuevo/',views.nuevo_proveedor,name='nuevo_proveedor'),
    path('proveedores/<int:id>/editar/',views.editar_proveedor,name='editar_proveedor'),
    path('proveedores/<int:id>/eliminar/',views.eliminar_proveedor,name='eliminar_proveedor'),
    path('proveedores/<int:id>/desactivar/',views.desactivar_proveedor,name='desactivar_proveedor'),
    path('proveedores/<int:id>/activar/',views.activar_proveedor,name='activar_proveedor'),
    path('proveedores/<int:id>/visitas/nueva/',views.agregar_visita_proveedor,name='agregar_visita_proveedor'),

    path('consumo/', views.ver_consumo, name='ver_consumo'),
    path('consumo/agregar/', views.agregar_consumo, name='agregar_consumo'),
    path('consumo/<int:pk>/detalle/', views.detalle_consumo, name='detalle_consumo'),
    path('consumo/<int:pk>/eliminar/', views.eliminar_consumo, name='eliminar_consumo'),
    path('api/productos/', views.buscar_productos_api, name='api_buscar_productos'),
    path('api/sugerencias/', views.buscar_sugerencias_api, name='api_buscar_sugerencias')
    
]