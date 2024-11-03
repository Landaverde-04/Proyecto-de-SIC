from django import views
from django.urls import path
from .views import filtrar_cuentas_por_tipo, inicio,catalogo_cuentas, libro_mayor,registrar_cuenta,transacciones,nueva_transaccion,ver_transaccion,api_libro_mayor, metodos_costeo, reportes_contables

urlpatterns = [
    path('', inicio, name='inicio'),
    path('catalogo/', catalogo_cuentas, name='catalogo_cuentas'),
    path('catalogo/nueva/', registrar_cuenta, name='nueva_cuenta'),
    path('transacciones/', transacciones, name='transacciones'),
    path('transacciones/nueva/', nueva_transaccion, name='nueva_transaccion'),
    path('transacciones/<int:id>/',ver_transaccion, name='ver_transaccion'), 
    path('libro_mayor/', libro_mayor, name='libro_mayor'),
    path('api/libro-mayor/', api_libro_mayor, name='api_libro_mayor'),
    path('api/filtrar-cuentas/', filtrar_cuentas_por_tipo, name='filtrar_cuentas_por_tipo'),
    path('metodos-costeo/', metodos_costeo, name='metodos-costeo'),
    path('reportes/', reportes_contables, name='reportes_contables')
]
