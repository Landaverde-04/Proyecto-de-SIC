from django.urls import path
from . import views

urlpatterns = [
    path('', views.hola, name='hola'),
    path('inicio', views.inicio, name='inicio'),
]