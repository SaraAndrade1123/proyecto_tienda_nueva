from django.urls import path

from . import views

urlpatterns = [
    path('', views.lista_salidas, name='lista_salidas'),
    path('registrar/', views.registrar_salida, name='registrar_salida'),
    path('<int:id>/', views.detalle_salida, name='detalle_salida'),
    path('motivos/', views.motivos_salida, name='motivos_salida'),
    path('motivos/cargar/', views.cargar_motivos_salida, name='cargar_motivos_salida'),
    path('motivos/<int:id>/editar/', views.editar_motivo_salida, name='editar_motivo_salida'),
    path('motivos/<int:id>/eliminar/', views.eliminar_motivo_salida, name='eliminar_motivo_salida'),
]