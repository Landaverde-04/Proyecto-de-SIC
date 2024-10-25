from django.urls import path
from .views import inicio,catalogo_cuentas,registrar_cuenta,editar_cuenta,eliminar_cuenta,transacciones,nueva_transaccion

urlpatterns = [
    path('', inicio, name='inicio'),
    path('catalogo/', catalogo_cuentas, name='catalogo_cuentas'),
    path('catalogo/nueva/', registrar_cuenta, name='nueva_cuenta'),
    path('catalogo/<int:pk>/editar/', editar_cuenta, name='editar_cuenta'),  # URL para editar cuenta
    path('catalogo/<int:pk>/eliminar/', eliminar_cuenta, name='eliminar_cuenta'), 
    path('transacciones/', transacciones, name='transacciones'),
    path('transacciones/nueva/', nueva_transaccion, name='nueva_transaccion'),
]
