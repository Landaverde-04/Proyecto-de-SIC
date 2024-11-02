from django import forms
from .models import Cuenta, Transaccion, Movimiento  

class CuentaForm(forms.ModelForm):
    class Meta:
        model = Cuenta
        fields = ['codigo', 'nombre']  # Los campos que quieres manejar en el formulario

class TransaccionForm(forms.ModelForm):
    class Meta:
        model = Transaccion
        fields = ['fecha']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
        }

class MovimientoForm(forms.ModelForm):
    class Meta:
        model = Movimiento  # Actualizado para reflejar el nombre del modelo
        fields = ['cuenta', 'debe', 'haber']

# Definir un FormSet para manejar múltiples movimientos en una transacción
MovimientoFormSet = forms.inlineformset_factory(
    Transaccion,
    Movimiento,  # Actualizado al nuevo modelo Movimiento
    form=MovimientoForm,
    extra=4  # Número de filas predeterminadas para movimientos
)

class LibroMayorFiltroForm(forms.Form):
    cuenta = forms.ModelChoiceField(
        queryset=Cuenta.objects.all(),
        required=False,
        label="Cuenta",
        help_text="Seleccione una cuenta para ver sus movimientos."
    )
    fecha_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Fecha de inicio"
    )
    fecha_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Fecha de fin"
    )
