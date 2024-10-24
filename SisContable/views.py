from django.urls import reverse_lazy
from django.shortcuts import render,redirect,get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, DeleteView
from .models import Cuenta
from .forms import CuentaForm

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