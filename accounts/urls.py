from django.urls import path
from . import views

urlpatterns = [
    path('registro/', views.registro, name='registro'),
    path('login/', views.iniciar_sesion, name='login'),
    path('logout/', views.cerrar_sesion, name='logout'),
    path('grupos/', views.grupos, name='grupos'),
    path('editar-grupo/<int:id_grupo>/', views.editar_grupo, name='editar_grupo'),
    path('agregar-usuario-grupo/<int:id_grupo>/', views.agregar_usuario_grupo, name='agregar_usuario_grupo'),
    path('eliminar-usuario-grupo/<int:id_grupo>/', views.eliminar_usuario_grupo, name='eliminar_usuario_grupo'),
    path('eliminar-grupo/<int:id_grupo>/', views.eliminar_grupo, name='eliminar_grupo'),
    path('permisos/', views.permisos, name='permisos'),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('perfil/eliminar/', views.eliminar_usuario, name='eliminar_usuario'),
]