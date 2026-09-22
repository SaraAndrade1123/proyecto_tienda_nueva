from django.urls import path
from . import views


urlpatterns = [
    
    path('lista_productos/', views.lista_productos, name='lista_productos'),
    path('crear/', views.crear_producto, name='crear_producto'),
    path('editar/<int:id>/', views.editar_producto, name='editar_producto'),
    path('eliminar/<int:id>/', views.eliminar_producto, name='eliminar_producto'),
    path('stock/aumentar/<int:id>/', views.aumentar_stock, name='aumentar_stock'),
    path('stock/disminuir/<int:id>/', views.disminuir_stock, name='disminuir_stock'),
    
]   