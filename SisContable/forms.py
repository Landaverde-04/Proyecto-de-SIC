from django import forms
from .models import Cuenta, Transaccion, Movimiento,Proyecto, CostoDirecto, CostoIndirecto, PeriodoContable
from django.core.exceptions import ValidationError

class CuentaForm(forms.ModelForm):
    class Meta:
        model = Cuenta
        fields = ['codigo', 'nombre']  # Los campos que quieres manejar en el formulario

class TransaccionForm(forms.ModelForm):
    periodo_contable = forms.ModelChoiceField(
        queryset=PeriodoContable.objects.all(),
        label="Periodo Contable",
        help_text="Seleccione el periodo contable"
    )

    class Meta:
        model = Transaccion
        fields = ['fecha', 'periodo_contable']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_periodo_contable(self):
        # Obtener el periodo contable seleccionado
        periodo_contable = self.cleaned_data.get('periodo_contable')
        
        # Verificar si el periodo contable está cerrado
        if periodo_contable and periodo_contable.cerrado:
            raise ValidationError("No se puede crear una transacción en un periodo contable cerrado.")
        
        return periodo_contable

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

class CostoDirectoForm(forms.ModelForm):
    class Meta:
        model = CostoDirecto
        fields = ['nombre', 'salario_mensual', 'cantidad_empleados']
        labels = {
            'nombre': 'Nombre del Puesto',
            'salario_mensual': 'Salario Mensual',
            'cantidad_empleados': 'Cantidad de Empleados'
        }
        widgets = {
            'salario_mensual': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'cantidad_empleados': forms.NumberInput(attrs={'min': '1'}),
        }


class CostoIndirectoForm(forms.ModelForm):
    class Meta:
        model = CostoIndirecto
        fields = ['nombre', 'descripcion', 'monto']


class ProyectoForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = ['nombre', 'descripcion', 'puntos_funcion_total', 'productividad', 'costos_directos', 'costos_indirectos']
        widgets = {
            'costos_directos': forms.CheckboxSelectMultiple,
            'costos_indirectos': forms.CheckboxSelectMultiple,
        }

    def save(self, commit=True):
        # Primero, guarda el proyecto sin relaciones Many-to-Many para obtener un ID
        proyecto = super().save(commit=False)
        proyecto.save()  # Guarda el proyecto para que tenga un ID

        # Ahora que el proyecto tiene un ID, podemos guardar las relaciones Many-to-Many
        self.save_m2m()

        # Realizar los cálculos ahora que las relaciones están establecidas
        proyecto.calcular_esfuerzo_total()
        proyecto.calcular_duracion_total()
        proyecto.calcular_costo_total()

        # Guarda los resultados finales después de los cálculos
        proyecto.save()

        return proyecto
    
class FechaFiltroForm(forms.Form):
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

    
class PeriodoContableForm(forms.ModelForm):
    class Meta:
        model = PeriodoContable
        fields = ['año', 'inicio', 'fin']
        widgets = {
            'inicio': forms.DateInput(attrs={'type': 'date'}),
            'fin': forms.DateInput(attrs={'type': 'date'}),
        }

class PeriodoContableFiltroForm(forms.Form):
    periodo_contable = forms.ModelChoiceField(
        queryset=PeriodoContable.objects.all(),
        label="Periodo Contable",
        help_text="Seleccione el periodo contable para filtrar el estado de resultados"
    )