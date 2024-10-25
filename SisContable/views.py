from django.urls import reverse_lazy
from django.db import transaction
from django.shortcuts import render,redirect,get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, DeleteView
from django.forms import inlineformset_factory,formset_factory
from .models import Cuenta,Transaccion, CuentaTransaccion
from .forms import CuentaForm,TransaccionForm, CuentaTransaccionForm,CuentaTransaccionFormSet

# Vista para la página de inicio
def inicio(request):
    return render(request, 'inicio.html')

def catalogo_cuentas(request):
    cuentas = Cuenta.objects.all().order_by('codigo')  # Ordenar por el campo 'codigo'
    return render(request, 'catalogo_cuentas.html', {'cuentas': cuentas})

def registrar_cuenta(request):
    if request.method == 'POST':
        form = CuentaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('catalogo_cuentas')  # Redirigir al catálogo de cuentas después de guardar
    else:
        form = CuentaForm()
    
    return render(request, 'registrar_cuenta.html', {'form': form})

def editar_cuenta(request, pk):
    cuenta = get_object_or_404(Cuenta, pk=pk)
    if request.method == 'POST':
        form = CuentaForm(request.POST, instance=cuenta)
        if form.is_valid():
            form.save()
            return redirect('catalogo_cuentas')  # Redirigir al catálogo después de editar
    else:
        form = CuentaForm(instance=cuenta)
    
    return render(request, 'editar_catalogo.html', {'form': form, 'cuenta': cuenta})

def eliminar_cuenta(request, pk):
    cuenta = get_object_or_404(Cuenta, pk=pk)
    if request.method == 'POST':
        cuenta.delete()
        return redirect('catalogo_cuentas')  # Redirigir al catálogo después de eliminar
    return render(request, 'catalogo_cuentas.html')

CuentaTransaccionFormSet = inlineformset_factory(
    Transaccion, 
    CuentaTransaccion, 
    form=CuentaTransaccionForm, 
    extra=1  # Cantidad de formularios de cuenta por defecto
)

# Vista principal para gestionar transacciones
def transacciones(request):
    transacciones = Transaccion.objects.all()  # Listar todas las transacciones

    if request.method == 'POST':
        transaccion_form = TransaccionForm(request.POST)
        formset = CuentaTransaccionFormSet(request.POST)

        if transaccion_form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():  # Inicia una transacción atómica
                    transaccion = transaccion_form.save()  # Guarda la transacción
                    formset.instance = transaccion  # Asigna la transacción al formset
                    formset.save()  # Guarda todas las cuentas asociadas a la transacción

                return redirect('transacciones')  # Redirigir al listado después de guardar
            except Exception as e:
                print(f"Error al guardar la transacción: {e}")
        else:
            print(f"Errores en el formulario de transacción: {transaccion_form.errors}")
            print(f"Errores en el formset: {formset.errors}")

    else:
        transaccion_form = TransaccionForm()
        formset = CuentaTransaccionFormSet()

    return render(request, 'transacciones.html', {
        'transaccion_form': transaccion_form,
        'formset': formset,
        'transacciones': transacciones,
    })

def nueva_transaccion(request):
    cuentas = Cuenta.objects.all()  # Obtener todas las cuentas disponibles

    if request.method == 'POST':
        transaccion_form = TransaccionForm(request.POST)
        formset = CuentaTransaccionFormSet(request.POST)

        if transaccion_form.is_valid() and formset.is_valid():
            total_debe = 0
            total_haber = 0

            # Validar la partida doble
            for form in formset:
                debe = form.cleaned_data.get('debe', 0)
                haber = form.cleaned_data.get('haber', 0)

                total_debe += debe
                total_haber += haber

            if total_debe != total_haber:
                formset.add_error(None, f"La partida doble no está equilibrada: Debe ({total_debe}) y Haber ({total_haber}) no coinciden.")
            else:
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
        formset = CuentaTransaccionFormSet(queryset=CuentaTransaccion.objects.none())  # Para mostrar filas vacías

    return render(request, 'nueva_transaccion.html', {
        'transaccion_form': transaccion_form,
        'formset': formset,
        'cuentas': cuentas,
    })