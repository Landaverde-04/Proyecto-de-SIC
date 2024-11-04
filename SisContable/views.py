import datetime
from django.forms import ValidationError, inlineformset_factory
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.db.models import Sum, F, Case, When, Value, DecimalField
from django.db import transaction, models
from django.shortcuts import render, redirect, get_object_or_404
from .models import Cuenta, Transaccion, Movimiento
from .forms import CuentaForm, LibroMayorFiltroForm, TransaccionForm, MovimientoForm, MovimientoFormSet

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
                    # Guarda la transacción inicial sin calcular los totales aún
                    transaccion = transaccion_form.save()

                    # Asocia y guarda los movimientos
                    formset.instance = transaccion
                    formset.save()

                    # Calcula y valida los totales en tiempo real
                    total_debe, total_haber = transaccion.calcular_totales()
                    
                    if total_debe != total_haber:
                        raise ValidationError("La partida doble no está equilibrada: el total del Debe debe ser igual al total del Haber.")

                    # Actualiza los saldos de las cuentas involucradas en la transacción
                    transaccion.actualizar_saldos()

                    # Redirige a la lista de transacciones después de guardar
                    return redirect('transacciones')

            except ValidationError as e:
                # Manejo de errores de validación
                transaccion_form.add_error(None, e.message)
            except Exception as e:
                print(f"Error al guardar la transacción: {e}")
        else:
            print(f"Errores en el formulario de transacción: {transaccion_form.errors}")
            print(f"Errores en el formset: {formset.errors}")
    else:
        transaccion_form = TransaccionForm()
        formset = MovimientoFormSet(queryset=Movimiento.objects.none())

    return render(request, 'nueva_transaccion.html', {
        'transaccion_form': transaccion_form,
        'formset': formset,
    })

def ver_transaccion(request, id):
    transaccion = get_object_or_404(Transaccion, id_transaccion=id)
    movimientos = transaccion.movimientos.all()  # Obtiene todos los movimientos asociados a la transacción
    return render(request, 'ver_transaccion.html', {
        'transaccion': transaccion,
        'movimientos': movimientos,
    })

# views.py

from django.shortcuts import render
from .models import Movimiento, Cuenta

def libro_mayor(request):
    form = LibroMayorFiltroForm(request.GET or None)
    cuentas = Cuenta.objects.all()  # Para el menú desplegable de cuentas
    movimientos = Movimiento.objects.none()  # Inicializar movimientos como vacío

    # Inicializar los totales y saldo
    total_debe = 0
    total_haber = 0
    saldo = 0
    saldo_tipo = ""

    if form.is_valid():
        cuenta = form.cleaned_data.get('cuenta')
        fecha_inicio = form.cleaned_data.get('fecha_inicio')
        fecha_fin = form.cleaned_data.get('fecha_fin')

        # Filtrar movimientos sólo si una cuenta ha sido seleccionada
        if cuenta:
            movimientos = Movimiento.objects.filter(cuenta=cuenta)

            # Aplicar filtros de fecha si existen
            if fecha_inicio:
                movimientos = movimientos.filter(transaccion__fecha__gte=fecha_inicio)
            if fecha_fin:
                movimientos = movimientos.filter(transaccion__fecha__lte=fecha_fin)

            # Calcular el total del debe y haber
            for movimiento in movimientos:
                total_debe += movimiento.debe
                total_haber += movimiento.haber

            # Calcular el saldo y determinar el tipo
            if cuenta.get_tipo_cuenta() in ["Activo", "Gastos"]:
                saldo = total_debe - total_haber
            else:  # Pasivo, Patrimonio y Ventas
                saldo = total_haber - total_debe

            if saldo > 0:
                saldo_tipo = "Saldo Deudor" if cuenta.get_tipo_cuenta() in ["Activo", "Gastos"] else "Saldo Acreedor"
            elif saldo < 0:
                saldo_tipo = "Saldo Acreedor" if cuenta.get_tipo_cuenta() in ["Activo", "Gastos"] else "Saldo Deudor"
            else:
                saldo_tipo = "Cuenta Saldada"

    return render(request, 'libro_mayor.html', {
        'form': form,
        'cuentas': cuentas,
        'movimientos': movimientos,
        'total_debe': total_debe,
        'total_haber': total_haber,
        'saldo': abs(saldo),  # Mostrar el saldo como valor absoluto
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
    
    movimientos = Movimiento.objects.select_related('cuenta', 'transaccion')

    # Filtrar por cuenta si se ha seleccionado una
    if cuenta_id:
        movimientos = movimientos.filter(cuenta_id=cuenta_id)

    # Filtrar por fecha de inicio y fecha de fin si están presentes
    if fecha_inicio:
        fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        movimientos = movimientos.filter(transaccion__fecha__gte=fecha_inicio)
    if fecha_fin:
        fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d')
        movimientos = movimientos.filter(transaccion__fecha__lte=fecha_fin)

    # Preparar los datos para la respuesta JSON
    movimientos_data = []
    for mov in movimientos:
        movimientos_data.append({
            'fecha': mov.transaccion.fecha.strftime('%Y-%m-%d'),
            'numero_transaccion': mov.transaccion.id_transaccion,
            'descripcion': mov.cuenta.nombre,
            'debe': float(mov.debe),
            'haber': float(mov.haber),
        })

    # Devolver los datos en formato JSON
    return JsonResponse({'movimientos': movimientos_data})

def metodos_costeo(request):
    return render(request, 'metodos-costeo.html')

def reportes_contables(request):
    return render(request, 'reportes_contables.html')

def balance_general(request):
    # Filtrar cuentas de Activo, Pasivo y Patrimonio individualmente y luego unir las consultas
    activos = Cuenta.objects.filter(codigo__startswith='1')
    pasivos = Cuenta.objects.filter(codigo__startswith='2')
    patrimonio = Cuenta.objects.filter(codigo__startswith='3')

    # Concatenar los tres QuerySets en una lista de cuentas
    cuentas_balance = list(activos) + list(pasivos) + list(patrimonio)

    # Anotar Debe y Haber para cada cuenta según el tipo
    for cuenta in cuentas_balance:
        if cuenta.codigo.startswith('1'):  # Activos
            cuenta.debe = cuenta.saldo
            cuenta.haber = 0
        elif cuenta.codigo.startswith('2') or cuenta.codigo.startswith('3'):  # Pasivos y Patrimonio
            cuenta.debe = 0
            cuenta.haber = cuenta.saldo

    # Calcular el total de Debe y Haber
    total_debe = sum(cuenta.debe for cuenta in cuentas_balance)
    total_haber = sum(cuenta.haber for cuenta in cuentas_balance)

    # Calcular la diferencia entre Haber y Debe
    resultado_final = total_haber - total_debe
    es_utilidad = resultado_final > 0  # Si es positivo, es utilidad; si no, es pérdida

    context = {
        'cuentas_balance': cuentas_balance,
        'total_debe': total_debe,
        'total_haber': total_haber,
        'resultado_final': abs(resultado_final),  # Mostrar siempre el valor absoluto
        'es_utilidad': es_utilidad,
    }
    return render(request, 'balance_general.html', context)