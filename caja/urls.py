from django.urls import path

from . import views

urlpatterns = [
    path('', views.caja_hoy, name='caja_hoy'),
    path('abrir/', views.abrir_caja, name='abrir_caja'),
    path('historial/', views.historial_cajas, name='historial_cajas'),
    path('cobrar/', views.cobrar_carrito, name='cobrar_carrito'),
    path('<int:id>/', views.detalle_caja, name='detalle_caja'),
    path('<int:id>/cerrar/', views.cerrar_caja, name='cerrar_caja'),
    path('<int:id>/borrar-prueba/', views.borrar_caja_prueba, name='borrar_caja_prueba'),
    path('<int:id>/pagos/nuevo/', views.registrar_pago, name='registrar_pago'),
    path('pagos/<int:id>/eliminar/', views.eliminar_pago, name='eliminar_pago'),
]