from django.http import HttpResponse
from django.urls import path
from . import views

urlpatterns = [
    path('', views.informacion_tienda, name='informacion_tienda'),

    #path('proveedores/', views.lista_proveedores, name='lista_proveedores'),
    #path('proveedores/nuevo/', views.crear_proveedor, name='crear_proveedor'),
    #path('proveedores/editar/<int:pk>/', views.editar_proveedor, name='editar_proveedor'),

    path('consumo/', views.ver_consumo, name='ver_consumo'),
]