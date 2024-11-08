from django import views
from django.urls import path
from .views import crear_costo_directo_ajax, detalle_proyecto, editar_costo_directo, editar_costo_indirecto, editar_proyecto, eliminar_costo_directo, eliminar_costo_indirecto, filtrar_cuentas_por_tipo, inicio,catalogo_cuentas, libro_mayor,registrar_cuenta,transacciones,nueva_transaccion,ver_transaccion,api_libro_mayor, metodos_costeo, reportes_contables, balance_general,crear_costo_indirecto_ajax,nuevo_proyecto, balance_comprobacion, estado_resultados, crear_periodo_contable, capital_social, cerrar_periodo_contable

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
    path('reportes/', reportes_contables, name='reportes_contables'),
    path('balance-general/', balance_general, name='balance_general'),
    path('costos-indirectos/crear/ajax/',crear_costo_indirecto_ajax, name='crear_costo_indirecto_ajax'),
    path('costos-directos/crear/ajax/', crear_costo_directo_ajax, name='crear_costo_directo_ajax'),
    path('nuevo-proyecto/', nuevo_proyecto, name='nuevo_proyecto'),
    path('balance-comprobacion/', balance_comprobacion, name='balance_comprobacion'),
    path('estado-resultados/', estado_resultados, name='estado_resultados'),
    path('crear-periodo-contable/', crear_periodo_contable, name='crear_periodo_contable'),
    path('capital-social/', capital_social, name='capital_social'),
    path('cerrar-periodo-contable/<int:periodo_id>/', cerrar_periodo_contable, name='cerrar_periodo_contable'),
    path('editar-costo-indirecto/<int:id>/', editar_costo_indirecto, name='editar_costo_indirecto'),
    path('eliminar-costo-indirecto/<int:id>/', eliminar_costo_indirecto, name='eliminar_costo_indirecto'),
    path('editar-costo-directo/<int:id>/', editar_costo_directo, name='editar_costo_directo'),
    path('eliminar-costo-directo/<int:id>/', eliminar_costo_directo, name='eliminar_costo_directo'),
    path('editar-proyecto/<int:id>/', editar_proyecto, name='editar_proyecto'),
    path('detalle-proyecto/<int:id>/', detalle_proyecto, name='detalle_proyecto'),
    
]
