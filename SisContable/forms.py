from django import forms
from .models import Cuenta,Transaccion, CuentaTransaccion

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

class CuentaTransaccionForm(forms.ModelForm):
    class Meta:
        model = CuentaTransaccion
        fields = ['cuenta', 'debe', 'haber']

CuentaTransaccionFormSet = forms.inlineformset_factory(
    Transaccion,
    CuentaTransaccion,
    form=CuentaTransaccionForm,
    extra=4  # Número de filas predeterminadas que quieres mostrar
 
)