from django.urls import path
from . import views

urlpatterns = [
    path('', views.informe_ingresos, name='informe_ingresos'),
]