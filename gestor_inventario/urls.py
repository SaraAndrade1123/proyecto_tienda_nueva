from django.http import HttpResponse
from django.urls import path
from . import views

urlpatterns = [
    path('', views.informacion_tienda, name='informacion_tienda'),
    
]
