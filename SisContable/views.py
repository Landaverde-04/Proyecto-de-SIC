import datetime
from django.forms import ValidationError, inlineformset_factory
from django.http import JsonResponse
from django.urls import reverse
from django.db.models import Sum, F, Case, When, Value, DecimalField, Q
from django.db import transaction, models
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .models import Cuenta, Transaccion, Movimiento,Proyecto, CostoDirecto, CostoIndirecto, PeriodoContable
from .forms import CuentaForm, LibroMayorFiltroForm, TransaccionForm, MovimientoForm, MovimientoFormSet,ProyectoForm, CostoDirectoForm, CostoIndirectoForm, FechaFiltroForm, PeriodoContableForm, PeriodoContableFiltroForm
from django.utils import timezone
from datetime import datetime



# Vista para la página de inicio
def inicio(request):
    return render(request, 'inicio.html')

def catalogo_cuentas(request):
    cuentas = Cuenta.objects.all().order_by('codigo')
    return render(request, 'catalogo_cuentas.html', {'cuentas': cuentas})

def registrar_cuenta(request):
    if request.method == 'POST':
        form = CuentaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('catalogo_cuentas')
    else:
        form = CuentaForm()
    
    return render(request, 'registrar_cuenta.html', {'form': form})


# Actualización del inlineformset_factory para reflejar el cambio a Movimiento
MovimientoFormSet = inlineformset_factory(
    Transaccion, 
    Movimiento, 
    form=MovimientoForm, 
    extra=4
)

# Vista para gestionar las transacciones
def transacciones(request):
    transacciones = Transaccion.objects.all()

    if request.method == 'POST':
        transaccion_form = TransaccionForm(request.POST)
        formset = MovimientoFormSet(request.POST)

        if transaccion_form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    transaccion = transaccion_form.save()
                    formset.instance = transaccion
                    formset.save()
                return redirect('transacciones')
            except Exception as e:
                print(f"Error al guardar la transacción: {e}")
        else:
            print(f"Errores en el formulario de transacción: {transaccion_form.errors}")
            print(f"Errores en el formset: {formset.errors}")

    else:
        transaccion_form = TransaccionForm()
        formset = MovimientoFormSet()

    return render(request, 'transacciones.html', {
        'transaccion_form': transaccion_form,
        'formset': formset,
        'transacciones': transacciones,
    })

def nueva_transaccion(request):
    if request.method == 'POST':
        transaccion_form = TransaccionForm(request.POST)
        formset = MovimientoFormSet(request.POST)

        if transaccion_form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Guardar la transacción con el periodo contable seleccionado
                    transaccion = transaccion_form.save()

                    # Asociar cada movimiento al periodo contable de la transacción y guardar
                    formset.instance = transaccion
                    movimientos = formset.save(commit=False)
                    for movimiento in movimientos:
                        movimiento.periodo_contable = transaccion.periodo_contable
                        movimiento.save()
                    
                    # Validar la partida doble
                    total_debe, total_haber = transaccion.calcular_totales()
                    if total_debe != total_haber:
                        raise ValidationError("La partida doble no está equilibrada: el total del Debe debe ser igual al total del Haber.")

                    # Actualizar los saldos de las cuentas involucradas
                    transaccion.actualizar_saldos()

                    return redirect('transacciones')

            except ValidationError as e:
                transaccion_form.add_error(None, e.message)
            except Exception as e:
                print(f"Error al guardar la transacción: {e}")
        else:
            # Imprimir errores de validación para depuración
            print(f"Errores en el formulario de transacción: {transaccion_form.errors}")
            print(f"Errores en el formset: {formset.errors}")
    else:
        # Inicializar formularios vacíos para una nueva transacción y sus movimientos
        transaccion_form = TransaccionForm()
        formset = MovimientoFormSet(queryset=Movimiento.objects.none())

    return render(request, 'nueva_transaccion.html', {
        'transaccion_form': transaccion_form,
        'formset': formset,
    })

def crear_periodo_contable(request):
    if request.method == 'POST':
        form = PeriodoContableForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Periodo contable creado exitosamente.")
            return redirect('inicio')  # Cambia 'inicio' a la vista o URL que desees usar después de la creación
        else:
            messages.error(request, "Por favor corrige los errores a continuación.")
    else:
        form = PeriodoContableForm()
    
    return render(request, 'crear_periodo_contable.html', {'form': form})


def ver_transaccion(request, id):
    transaccion = get_object_or_404(Transaccion, id_transaccion=id)
    movimientos = transaccion.movimientos.all()  # Obtiene todos los movimientos asociados a la transacción
    return render(request, 'ver_transaccion.html', {
        'transaccion': transaccion,
        'movimientos': movimientos,
    })

def libro_mayor(request):
    form = LibroMayorFiltroForm(request.GET or None)
    cuentas = Cuenta.objects.all()  # Para el menú desplegable de cuentas
    movimientos = Movimiento.objects.all()  # Inicializar con todos los movimientos

    total_debe = 0
    total_haber = 0
    saldo = 0
    saldo_tipo = ""

    # Filtros simultáneos según el formulario
    if form.is_valid():
        cuenta = form.cleaned_data.get('cuenta')
        fecha_inicio = form.cleaned_data.get('fecha_inicio')
        fecha_fin = form.cleaned_data.get('fecha_fin')

        # Filtrar movimientos progresivamente
        if cuenta:
            movimientos = movimientos.filter(cuenta=cuenta)
        if fecha_inicio:
            movimientos = movimientos.filter(transaccion__fecha__gte=fecha_inicio)
        if fecha_fin:
            movimientos = movimientos.filter(transaccion__fecha__lte=fecha_fin)

        # Calcular totales y saldo
        for movimiento in movimientos:
            total_debe += movimiento.debe
            total_haber += movimiento.haber

        # Determinar saldo y tipo
        if cuenta and cuenta.get_tipo_cuenta() in ["Activo", "Gastos"]:
            saldo = total_debe - total_haber
        else:
            saldo = total_haber - total_debe

        saldo_tipo = "Saldo Deudor" if saldo > 0 else "Saldo Acreedor" if saldo < 0 else "Cuenta Saldada"

    return render(request, 'libro_mayor.html', {
        'form': form,
        'cuentas': cuentas,
        'movimientos': movimientos,
        'total_debe': total_debe,
        'total_haber': total_haber,
        'saldo': abs(saldo),  # Mostrar saldo absoluto
        'saldo_tipo': saldo_tipo,
    })

def filtrar_cuentas_por_tipo(request):
    tipo_cuenta = request.GET.get('tipo_cuenta')
    if tipo_cuenta:
        # Filtra las cuentas cuyo código comienza con el número correspondiente al tipo
        cuentas = Cuenta.objects.filter(codigo__startswith=tipo_cuenta)
        cuentas_data = [{'id': cuenta.id, 'codigo': cuenta.codigo, 'nombre': cuenta.nombre} for cuenta in cuentas]
    else:
        cuentas_data = []
    return JsonResponse({'cuentas': cuentas_data})

def api_libro_mayor(request):
    cuenta_id = request.GET.get('cuenta')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    if not cuenta_id:
        return JsonResponse({"movimientos": [], "error": "Cuenta no especificada"}, status=400)

    movimientos = Movimiento.objects.filter(cuenta_id=cuenta_id)

    if fecha_inicio:
        try:
            fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            movimientos = movimientos.filter(transaccion__fecha__gte=fecha_inicio_obj)
        except ValueError:
            return JsonResponse({"movimientos": [], "error": "Fecha de inicio no válida"}, status=400)

    if fecha_fin:
        try:
            fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d')
            movimientos = movimientos.filter(transaccion__fecha__lte=fecha_fin_obj)
        except ValueError:
            return JsonResponse({"movimientos": [], "error": "Fecha de fin no válida"}, status=400)

    movimientos_data = [{
        "fecha": movimiento.transaccion.fecha.strftime('%Y-%m-%d'),
        "numero_transaccion": movimiento.transaccion.id_transaccion,  # Cambiado para reflejar el campo correcto
        "descripcion": movimiento.transaccion.periodo_contable.año,  # O cualquier otro campo que quieras incluir
        "debe": float(movimiento.debe),
        "haber": float(movimiento.haber)
    } for movimiento in movimientos]

    return JsonResponse({"movimientos": movimientos_data})


def metodos_costeo(request):
    return render(request, 'metodos-costeo.html')

def reportes_contables(request):
    return render(request, 'reportes_contables.html')

def balance_general(request):
    form = PeriodoContableFiltroForm(request.GET or None)
    cuentas_balance = []
    total_debe = 0
    total_haber = 0
    periodo_contable = None
    codigo_capital = "31"  # Cambia esto si tu cuenta de capital tiene un código diferente

    if form.is_valid():
        periodo_contable = form.cleaned_data.get('periodo_contable')

        # Cargar todas las cuentas de Activo, Pasivo y Patrimonio
        cuentas_balance = Cuenta.objects.filter(
            Q(codigo__startswith='1') | Q(codigo__startswith='2') | Q(codigo__startswith='3')
        )

        # Agregar debe y haber a cada cuenta en función del periodo contable
        for cuenta in cuentas_balance:
            # Filtrar movimientos de la cuenta en el periodo contable seleccionado
            movimientos = Movimiento.objects.filter(
                transaccion__periodo_contable=periodo_contable,
                cuenta=cuenta
            )
            # Calcular el total de 'debe' y 'haber' basados en el periodo
            cuenta.debe = movimientos.aggregate(total_debe=Sum('debe'))['total_debe'] or 0
            cuenta.haber = movimientos.aggregate(total_haber=Sum('haber'))['total_haber'] or 0

            # Si es la cuenta de capital, usamos el saldo directamente de la base de datos
            if cuenta.codigo == codigo_capital:
                cuenta.saldo = cuenta.saldo  # Usamos el saldo directamente
            else:
                cuenta.saldo = cuenta.haber - cuenta.debe

        # Calcular los totales de debe y haber para todas las cuentas
        total_debe = sum(cuenta.debe for cuenta in cuentas_balance)
        total_haber = sum(cuenta.haber for cuenta in cuentas_balance)

    context = {
        'form': form,
        'cuentas_balance': cuentas_balance,
        'total_debe': total_debe,
        'total_haber': total_haber,
        'periodo_contable': periodo_contable,
    }
    return render(request, 'balance_general.html', context)

def metodos_costeo(request):
    if request.method == 'POST':
        # Imprime todo el request.POST para ver todos los datos enviados
        print("Datos recibidos en POST:", request.POST)
        
        # Captura el tipo de formulario
        form_type = request.POST.get('form_type')
        print("Tipo de formulario recibido:", form_type)
        
        if form_type == 'costo_directo':
            form = CostoDirectoForm(request.POST)
            if form.is_valid():
                form.save()
                print("Costo Directo guardado exitosamente")
                return JsonResponse({'success': True, 'message': 'Costo Directo guardado'})
            else:
                print("Errores del formulario Costo Directo:", form.errors)
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        
        elif form_type == 'costo_indirecto':
            form = CostoIndirectoForm(request.POST)
            if form.is_valid():
                form.save()
                print("Costo Indirecto guardado exitosamente")
                return JsonResponse({'success': True, 'message': 'Costo Indirecto guardado'})
            else:
                print("Errores del formulario Costo Indirecto:", form.errors)
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)

        else:
            print("Formulario desconocido o tipo de formulario no especificado")
            return JsonResponse({'success': False, 'message': 'Formulario desconocido'}, status=400)

    # Obtener todos los proyectos y costos
    proyectos = Proyecto.objects.all()
    costos_directos = CostoDirecto.objects.all()
    costos_indirectos = CostoIndirecto.objects.all()
    
    # Calcular los totales
    total_costos_directos = sum(cd.total_con_prestaciones for cd in costos_directos)
    total_costos_indirectos = sum(ci.monto for ci in costos_indirectos)

    # Formularios para agregar costos
    form_ci = CostoIndirectoForm()
    form_cd = CostoDirectoForm()

    # Contexto para la plantilla
    context = {
        'proyectos': proyectos,
        'costos_directos': costos_directos,
        'costos_indirectos': costos_indirectos,
        'total_costos_directos': total_costos_directos,
        'total_costos_indirectos': total_costos_indirectos,
        'form_ci': form_ci,
        'form_cd': form_cd,
    }
    return render(request, 'metodos-costeo.html', context)

def crear_costo_directo_ajax(request):
    if request.method == 'POST':
        print("Datos recibidos en POST:", request.POST)
        form = CostoDirectoForm(request.POST)
        nombre = request.POST.get('nombre')
        
        if CostoDirecto.objects.filter(nombre=nombre).exists():
            print("Error: Nombre duplicado")
            return JsonResponse({'success': False, 'error': 'duplicate'}, status=400)
        
        if form.is_valid():
            costo = form.save()
            print("Costo guardado con éxito:", costo)
            return JsonResponse({
                'success': True,
                'costo': {
                    'id': costo.id,
                    'nombre': costo.nombre,
                    'salario_mensual': costo.salario_mensual,
                    'cantidad_empleados': costo.cantidad_empleados
                }
            })
        else:
            print("Errores de validación del formulario:", form.errors)
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    return JsonResponse({'success': False}, status=400)


# Crear Costo Indirecto con AJAX
def crear_costo_indirecto_ajax(request):
    if request.method == 'POST':
        form = CostoIndirectoForm(request.POST)
        nombre = request.POST.get('nombre')
        
        if CostoIndirecto.objects.filter(nombre=nombre).exists():
            return JsonResponse({'success': False, 'error': 'duplicate'}, status=400)
        
        if form.is_valid():
            costo = form.save()
            return JsonResponse({
                'success': True,
                'costo': {
                    'id': costo.id,  # Incluye el ID
                    'nombre': costo.nombre,
                    'descripcion': costo.descripcion,
                    'monto': costo.monto
                }
            })
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    return JsonResponse({'success': False}, status=400)

# Eliminar Costo Indirecto con AJAX
def eliminar_costo_indirecto(request, id):
    costo = get_object_or_404(CostoIndirecto, id=id)
    if request.method == 'POST':
        costo.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

# Eliminar Costo Directo con AJAX
def eliminar_costo_directo(request, id):
    costo = get_object_or_404(CostoDirecto, id=id)
    if request.method == 'POST':
        costo.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

# Editar Costo Indirecto con AJAX
def editar_costo_indirecto(request, id):
    if request.method == 'POST':
        costo = get_object_or_404(CostoIndirecto, id=id)
        form = CostoIndirectoForm(request.POST, instance=costo)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    return JsonResponse({'success': False}, status=400)

# Editar Costo Directo con AJAX
def editar_costo_directo(request, id):
    if request.method == 'POST':
        costo = get_object_or_404(CostoDirecto, id=id)
        form = CostoDirectoForm(request.POST, instance=costo)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    return JsonResponse({'success': False}, status=400)

def nuevo_proyecto(request):
    if request.method == 'POST':
        form = ProyectoForm(request.POST)
        if form.is_valid():
            proyecto = form.save(commit=False)
            
            # Asegurarse de calcular y guardar en el orden correcto
            proyecto.calcular_esfuerzo_total()
            proyecto.calcular_duracion_total()
            proyecto.calcular_costo_total()

            proyecto.save()
            form.save_m2m()  # Guarda las relaciones Many-to-Many
            
            messages.success(request, 'Proyecto creado exitosamente.')
            return redirect('metodos-costeo')
        else:
            messages.error(request, 'Hubo un error al crear el proyecto.')
    else:
        form = ProyectoForm()
    return render(request, 'nuevo_proyecto.html', {'form': form})

# Vista para editar un proyecto en una nueva página
def editar_proyecto(request, id):
    proyecto = get_object_or_404(Proyecto, id=id)
    
    # Calcular total de empleados sin intentar guardarlo directamente en la base de datos
    proyecto.total_empleados = proyecto.calcular_total_empleados()

    if request.method == 'POST':
        form = ProyectoForm(request.POST, instance=proyecto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Proyecto actualizado exitosamente.')
            return redirect('detalle_proyecto', id=proyecto.id)
        else:
            messages.error(request, 'Hubo un error al actualizar el proyecto.')
    else:
        form = ProyectoForm(instance=proyecto)

    return render(request, 'editar_proyecto.html', {'form': form, 'proyecto': proyecto})

# Vista para ver el detalle de un proyecto
def detalle_proyecto(request, id):
    proyecto = get_object_or_404(Proyecto, id=id)
    
    # Asegúrate de que `total_empleados` está calculado y accesible en el contexto
    proyecto.total_empleados = proyecto.calcular_total_empleados()

    return render(request, 'detalle_proyecto.html', {'proyecto': proyecto})

def balance_comprobacion(request):
    # Procesar el formulario de filtrado de fechas
    form = FechaFiltroForm(request.GET or None)
    fecha_inicio = form.cleaned_data.get('fecha_inicio') if form.is_valid() else None
    fecha_fin = form.cleaned_data.get('fecha_fin') if form.is_valid() else None

    # Obtener todas las cuentas
    cuentas = Cuenta.objects.all()

    # Filtrar los movimientos en función del rango de fechas
    movimientos = Movimiento.objects.all()
    if fecha_inicio:
        movimientos = movimientos.filter(transaccion__fecha__gte=fecha_inicio)
    if fecha_fin:
        movimientos = movimientos.filter(transaccion__fecha__lte=fecha_fin)

    # Calcular el saldo en base a los movimientos filtrados por cada cuenta
    cuentas_balance = cuentas.annotate(
        debe=Sum(
            Case(
                When(movimiento__in=movimientos, movimiento__debe__gt=0, then=F('movimiento__debe')),
                default=Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        ),
        haber=Sum(
            Case(
                When(movimiento__in=movimientos, movimiento__haber__gt=0, then=F('movimiento__haber')),
                default=Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        )
    ).filter(~Q(debe=0, haber=0))  # Filtrar cuentas que NO tengan ambos saldos en 0

    # Calcular los totales de Debe y Haber
    total_debe = cuentas_balance.aggregate(total=Sum('debe'))['total'] or 0
    total_haber = cuentas_balance.aggregate(total=Sum('haber'))['total'] or 0

    context = {
        'form': form,
        'cuentas_balance': cuentas_balance,
        'total_debe': total_debe,
        'total_haber': total_haber,
    }
    return render(request, 'balance_comprobacion.html', context)

def estado_resultados(request):
    form = PeriodoContableFiltroForm(request.GET or None)
    cuentas = []
    total_debe = 0
    total_haber = 0
    utilidad_bruta = 0
    es_utilidad = True

    if request.method == 'POST' and form.is_valid():
        periodo_contable = form.cleaned_data.get('periodo_contable')

        # Filtrar las cuentas de ingresos y gastos para calcular los totales
        cuentas_ingresos_gastos = Cuenta.objects.filter(
            Q(codigo__startswith='5') | Q(codigo__startswith='4')
        )

        # Calcular los totales de debe y haber antes del cierre
        for cuenta in cuentas_ingresos_gastos:
            movimientos = Movimiento.objects.filter(cuenta=cuenta, transaccion__periodo_contable=periodo_contable)
            total_debe += movimientos.aggregate(Sum('debe'))['debe__sum'] or 0
            total_haber += movimientos.aggregate(Sum('haber'))['haber__sum'] or 0

        # Verificar si el total de debe y haber están equilibrados
        if total_debe == total_haber:
            messages.error(request, "El cierre no se puede realizar porque el total de Debe y Haber ya están equilibrados.")
        else:
            # Crear una nueva transacción para el cierre
            with transaction.atomic():
                transaccion_cierre = Transaccion.objects.create(fecha=periodo_contable.fin, periodo_contable=periodo_contable)

                # Cerrar las cuentas de ingresos y gastos
                total_ingresos = 0
                total_gastos = 0

                for cuenta in cuentas_ingresos_gastos:
                    # Calcular el saldo actual de la cuenta
                    movimientos = Movimiento.objects.filter(cuenta=cuenta, transaccion__periodo_contable=periodo_contable)
                    debe_total = movimientos.aggregate(Sum('debe'))['debe__sum'] or 0
                    haber_total = movimientos.aggregate(Sum('haber'))['haber__sum'] or 0
                    saldo_actual = haber_total - debe_total if cuenta.codigo.startswith('5') else debe_total - haber_total

                    # Sumar el saldo a ingresos o gastos
                    if cuenta.codigo.startswith('5'):
                        total_ingresos += haber_total - debe_total
                    elif cuenta.codigo.startswith('4'):
                        total_gastos += debe_total - haber_total

                    # Crear el movimiento inverso para dejar el saldo en cero
                    if cuenta.codigo.startswith('5'):  # Cuenta de ingresos
                        Movimiento.objects.create(
                            transaccion=transaccion_cierre,
                            cuenta=cuenta,
                            debe=saldo_actual if saldo_actual > 0 else 0,
                            haber=0,
                            periodo_contable=periodo_contable
                        )
                    elif cuenta.codigo.startswith('4'):  # Cuenta de gastos
                        Movimiento.objects.create(
                            transaccion=transaccion_cierre,
                            cuenta=cuenta,
                            debe=0,
                            haber=abs(saldo_actual) if saldo_actual < 0 else saldo_actual,
                            periodo_contable=periodo_contable
                        )

                    # Establecer el saldo de la cuenta directamente en cero
                    cuenta.saldo = 0
                    cuenta.save()

                # Calcular utilidad o pérdida bruta y registrar el resultado en la cuenta 3102 o 3103
                utilidad_bruta = total_ingresos - total_gastos
                if utilidad_bruta > 0:
                    cuenta_utilidad = Cuenta.objects.get(codigo='3102')
                    Movimiento.objects.create(
                        transaccion=transaccion_cierre,
                        cuenta=cuenta_utilidad,
                        debe=0,
                        haber=utilidad_bruta,
                        periodo_contable=periodo_contable
                    )
                    # Actualizar el saldo de la cuenta de utilidad
                    cuenta_utilidad.saldo += utilidad_bruta
                    cuenta_utilidad.save()
                else:
                    cuenta_perdida = Cuenta.objects.get(codigo='3103')
                    Movimiento.objects.create(
                        transaccion=transaccion_cierre,
                        cuenta=cuenta_perdida,
                        debe=abs(utilidad_bruta),
                        haber=0,
                        periodo_contable=periodo_contable
                    )
                    # Actualizar el saldo de la cuenta de pérdida
                    cuenta_perdida.saldo += abs(utilidad_bruta)
                    cuenta_perdida.save()

                messages.success(request, "Estado de resultados cerrado exitosamente.")

    # Mostrar el estado de resultados (cálculos normales)
    if form.is_valid():
        periodo_contable = form.cleaned_data.get('periodo_contable')

        # Filtrar movimientos de acuerdo al periodo contable seleccionado y solo cuentas de ingresos y costos
        movimientos = Movimiento.objects.filter(
            transaccion__periodo_contable=periodo_contable,
            cuenta__codigo__startswith='4'
        ) | Movimiento.objects.filter(
            transaccion__periodo_contable=periodo_contable,
            cuenta__codigo__startswith='5'
        )

        # Obtener las cuentas de ingresos y costos asociadas a estos movimientos
        cuentas = movimientos.values(
            'cuenta__codigo', 'cuenta__nombre'
        ).annotate(
            debe=Sum('debe'),
            haber=Sum('haber')
        )

        # Calcular los totales de Debe y Haber
        total_debe = sum(cuenta['debe'] for cuenta in cuentas)
        total_haber = sum(cuenta['haber'] for cuenta in cuentas)

        # Calcular utilidad o pérdida bruta
        utilidad_bruta = total_haber - total_debe
        es_utilidad = utilidad_bruta >= 0  # Si es positivo, es utilidad; si es negativo, es pérdida

    context = {
        'form': form,
        'cuentas': cuentas,
        'total_debe': total_debe,
        'total_haber': total_haber,
        'utilidad_bruta': abs(utilidad_bruta),  # Mostrar siempre como valor positivo
        'es_utilidad': es_utilidad,             # True si es utilidad, False si es pérdida
    }
    return render(request, 'estado_resultados.html', context)

def capital_social(request):
    form = PeriodoContableFiltroForm(request.GET or None)
    cuentas = []
    total_debe = 0
    total_haber = 0
    es_aumento = True

    if request.method == 'POST' and form.is_valid():
        periodo_contable = form.cleaned_data.get('periodo_contable')

        # Filtrar las cuentas de capital social para calcular los totales
        cuentas_capital_social = Cuenta.objects.filter(
            Q(codigo__startswith='3') & ~Q(codigo='3101')
        )

        # Calcular los totales de debe y haber antes del cierre
        for cuenta in cuentas_capital_social:
            movimientos = Movimiento.objects.filter(cuenta=cuenta, transaccion__periodo_contable=periodo_contable)
            total_debe += movimientos.aggregate(Sum('debe'))['debe__sum'] or 0
            total_haber += movimientos.aggregate(Sum('haber'))['haber__sum'] or 0

        # Verificar si el total de debe y haber están equilibrados
        if total_debe == total_haber:
            messages.error(request, "El cierre no se puede realizar porque el total de Debe y Haber ya están equilibrados.")
            # Evitar el cierre sin redirigir, para que se mantenga el estado actual de la página
        else:
            # Crear una nueva transacción para el cierre
            with transaction.atomic():
                transaccion_cierre = Transaccion.objects.create(fecha=periodo_contable.fin, periodo_contable=periodo_contable)

                total_capital = 0

                for cuenta in cuentas_capital_social:
                    # Calcular el saldo actual de la cuenta
                    movimientos = Movimiento.objects.filter(cuenta=cuenta, transaccion__periodo_contable=periodo_contable)
                    debe_total = movimientos.aggregate(Sum('debe'))['debe__sum'] or 0
                    haber_total = movimientos.aggregate(Sum('haber'))['haber__sum'] or 0
                    saldo_actual = haber_total - debe_total if cuenta.codigo.startswith('3') else debe_total - haber_total

                    # Sumar el saldo al total de capital
                    total_capital += haber_total - debe_total

                    # Crear el movimiento inverso para dejar el saldo en cero
                    if saldo_actual > 0:
                        Movimiento.objects.create(
                            transaccion=transaccion_cierre,
                            cuenta=cuenta,
                            debe=saldo_actual,
                            haber=0,
                            periodo_contable=periodo_contable
                        )
                    elif saldo_actual < 0:
                        Movimiento.objects.create(
                            transaccion=transaccion_cierre,
                            cuenta=cuenta,
                            debe=0,
                            haber=abs(saldo_actual),
                            periodo_contable=periodo_contable
                        )

                    # Establecer el saldo de la cuenta directamente en cero
                    cuenta.saldo = 0
                    cuenta.save()

                # Registrar el resultado en la cuenta de Capital Social (3101)
                cuenta_capital_social = Cuenta.objects.get(codigo='3101')
                if total_capital > 0:
                    Movimiento.objects.create(
                        transaccion=transaccion_cierre,
                        cuenta=cuenta_capital_social,
                        debe=0,
                        haber=total_capital,
                        periodo_contable=periodo_contable
                    )
                    cuenta_capital_social.saldo += total_capital
                else:
                    Movimiento.objects.create(
                        transaccion=transaccion_cierre,
                        cuenta=cuenta_capital_social,
                        debe=abs(total_capital),
                        haber=0,
                        periodo_contable=periodo_contable
                    )
                    cuenta_capital_social.saldo += abs(total_capital)
                cuenta_capital_social.save()

                messages.success(request, "Capital social cerrado exitosamente.")

    # Mostrar el capital social calculado (cálculos normales)
    if form.is_valid():
        periodo_contable = form.cleaned_data.get('periodo_contable')

        # Filtrar movimientos de acuerdo al periodo contable seleccionado y solo cuentas de capital social, excluyendo la cuenta 3101
        movimientos = Movimiento.objects.filter(
            transaccion__periodo_contable=periodo_contable,
            cuenta__codigo__startswith='3'
        ).exclude(cuenta__codigo='3101')

        # Obtener las cuentas de capital social asociadas a estos movimientos
        cuentas = movimientos.values(
            'cuenta__codigo', 'cuenta__nombre'
        ).annotate(
            debe=Sum('debe'),
            haber=Sum('haber')
        )

        # Calcular los totales de Debe y Haber
        total_debe = sum(cuenta['debe'] for cuenta in cuentas)
        total_haber = sum(cuenta['haber'] for cuenta in cuentas)

    context = {
        'form': form,
        'cuentas': cuentas,
        'total_debe': total_debe,
        'total_haber': total_haber,
        'es_aumento': total_haber >= total_debe,  # True si es aumento de capital, False si es disminución
    }
    return render(request, 'estado_capital.html', context)

def cerrar_periodo_contable(request, periodo_id):
    periodo_contable = get_object_or_404(PeriodoContable, id=periodo_id)

    # Verificar si el periodo ya está cerrado
    if periodo_contable.cerrado:
        messages.error(request, "El periodo contable ya está cerrado.")
        return redirect(reverse('balance_general'))

    try:
        with transaction.atomic():
            print("Iniciando el cierre del periodo contable...")  # Depuración

            # Crear una transacción de cierre para este periodo contable
            transaccion_cierre = Transaccion.objects.create(
                fecha=timezone.now(),
                periodo_contable=periodo_contable
            )
            print(f"Transacción de cierre creada con ID {transaccion_cierre.id_transaccion}")  # Usar id_transaccion

            # 1. Saldar cuentas de Activo y Pasivo
            cuentas_saldar = Cuenta.objects.filter(
                Q(codigo__startswith='1') | Q(codigo__startswith='2')
            )

            for cuenta in cuentas_saldar:
                saldo_actual = cuenta.saldo
                print(f"Procesando cuenta {cuenta.codigo} con saldo {saldo_actual}")  # Depuración

                if saldo_actual != 0:
                    # Crear un movimiento inverso para saldar la cuenta
                    Movimiento.objects.create(
                        transaccion=transaccion_cierre,
                        cuenta=cuenta,
                        debe=saldo_actual if cuenta.codigo.startswith('2') else 0,
                        haber=saldo_actual if cuenta.codigo.startswith('1') else 0,
                        periodo_contable=periodo_contable  # Aseguramos el periodo contable
                    )
                    # Poner el saldo de la cuenta en 0
                    cuenta.saldo = 0
                    cuenta.save()
                    print(f"Cuenta {cuenta.codigo} saldada. Nuevo saldo: {cuenta.saldo}")  # Depuración

            # 2. Transferir el saldo de la cuenta "3101" a la cuenta "31"
            cuenta_3101 = Cuenta.objects.get(codigo="3101")
            saldo_3101 = cuenta_3101.saldo
            print(f"Saldo de la cuenta 3101 antes de transferir: {saldo_3101}")  # Depuración

            if saldo_3101 != 0:
                cuenta_31 = Cuenta.objects.get(codigo="31")
                # Crear el movimiento de transferencia en la transacción de cierre
                Movimiento.objects.create(
                    transaccion=transaccion_cierre,
                    cuenta=cuenta_31,
                    debe=0 if saldo_3101 > 0 else abs(saldo_3101),
                    haber=saldo_3101 if saldo_3101 > 0 else 0,
                    periodo_contable=periodo_contable  # Aseguramos el periodo contable
                )
                # Actualizar el saldo de la cuenta "31"
                cuenta_31.saldo += saldo_3101
                cuenta_31.save()
                print(f"Saldo de la cuenta 31 después de la transferencia: {cuenta_31.saldo}")  # Depuración

                # Poner el saldo de la cuenta "3101" en 0
                cuenta_3101.saldo = 0
                cuenta_3101.save()
                print(f"Cuenta 3101 saldada. Nuevo saldo: {cuenta_3101.saldo}")  # Depuración

            # 3. Marcar el periodo contable como cerrado
            periodo_contable.cerrado = True
            periodo_contable.save()
            print(f"Periodo contable {periodo_contable.año} cerrado: {periodo_contable.cerrado}")  # Depuración

            messages.success(request, "El periodo contable ha sido cerrado exitosamente.")

    except Exception as e:
        print(f"Error al cerrar el periodo contable: {e}")  # Depuración de errores
        messages.error(request, f"Ocurrió un error al cerrar el periodo contable: {e}")

    return redirect(reverse('balance_general'))