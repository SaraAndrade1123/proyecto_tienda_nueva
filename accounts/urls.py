from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('registro/', views.registro, name='registro'),
    path('login/',views.iniciar_sesion,name='login'),

    path('logout/', views.cerrar_sesion, name='logout'),

    path('home/', views.home, name='home'),

    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
]
