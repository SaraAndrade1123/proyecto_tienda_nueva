from django.urls import path
from . import views


urlpatterns = [

    path(
        'catalogo/',
        views.catalogo,
        name='catalogo'
    ),

]