from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Sum

VACACIONES_DIAS = 15
AGUINALDO_DIAS = 19
AFP = 0.0775
SEGURO_SOCIAL = 0.075
ICAF = 0.01

class Cuenta(models.Model):
    codigo = models.CharField(max_length=6, unique=True)
    nombre = models.CharField(max_length=100)
    saldo = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)  # Campo de saldo

    def get_tipo_cuenta(self):
        """Determina el tipo de cuenta basado en el primer dígito del código."""
        if not self.codigo or not self.codigo.isdigit():
            return "Código inválido"
        primer_digito = self.codigo[0]
        if primer_digito == '1':
            return "Activo"
        elif primer_digito == '2':
            return "Pasivo"
        elif primer_digito == '3':
            return "Patrimonio"
        elif primer_digito == '4':
            return "Gastos"
        elif primer_digito == '5':
            return "Ventas"
        else:
            return "Tipo de cuenta no definido"

    def actualizar_saldo(self, debe, haber):
        """Actualiza el saldo de la cuenta basado en su naturaleza."""
        tipo_cuenta = self.get_tipo_cuenta()
        if tipo_cuenta in ["Activo", "Gastos"]:
            self.saldo += debe - haber
        elif tipo_cuenta in ["Pasivo", "Patrimonio", "Ventas"]:
            self.saldo += haber - debe
        self.save()

    def __str__(self):
        return f"{self.codigo} - {self.nombre} - Saldo: {self.saldo}"


class Transaccion(models.Model):
    id_transaccion = models.AutoField(primary_key=True)
    fecha = models.DateField()

    def calcular_totales(self):
        """Calcula el total de Debe y Haber de la transacción sumando los movimientos asociados."""
        total_debe = self.movimientos.aggregate(total=Sum("debe"))["total"] or 0
        total_haber = self.movimientos.aggregate(total=Sum("haber"))["total"] or 0
        return total_debe, total_haber

    def actualizar_saldos(self):
        """Actualiza el saldo de cada cuenta involucrada en la transacción."""
        for movimiento in self.movimientos.all():
            cuenta = movimiento.cuenta
            cuenta.actualizar_saldo(movimiento.debe, movimiento.haber)

    def save(self, *args, **kwargs):
        """Guarda la transacción y actualiza los saldos de las cuentas relacionadas."""
        if not self.pk:
            super().save(*args, **kwargs)
        
        # Actualizar saldos de las cuentas involucradas
        self.actualizar_saldos()
        super().save()

    def __str__(self):
        return f"Transacción {self.id_transaccion} - {self.fecha}"


class Movimiento(models.Model):
    transaccion = models.ForeignKey(
        Transaccion, on_delete=models.CASCADE, related_name="movimientos"
    )
    cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE)
    debe = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    haber = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Transacción {self.transaccion.id_transaccion} - Cuenta {self.cuenta.codigo}: Debe {self.debe}, Haber {self.haber}"



# Modelo de Costos Indirectos (CI)
class CostosIndirectos(models.Model):
    nombre_costo = models.CharField(max_length=100)
    monto_mensual = models.DecimalField(max_digits=12, decimal_places=2)

    def calcular_costo_diario(self):
        # Costo diario es el mensual dividido por 30 días
        return self.monto_mensual / 30

    def calcular_costo_semanal(self):
        # Costo semanal es el diario multiplicado por 5.5 días de trabajo
        return self.calcular_costo_diario() * 5.5

    def calcular_costo_por_hora(self):
        # Costo por hora es el semanal dividido entre 44 horas laborales
        return self.calcular_costo_semanal() / 44

    def __str__(self):
        return f"{self.nombre_costo} - Monto mensual: {self.monto_mensual}"


# Modelo de Costos Directos (CD)
class CostosDirectos(models.Model):
    nombre_puesto = models.CharField(max_length=100)
    salario_mensual = models.DecimalField(max_digits=12, decimal_places=2)
    cantidad_empleados = models.IntegerField(default=1)

    def calcular_salario_diario(self):
        # Salario diario derivado del salario semanal
        return self.calcular_salario_semanal() / 5.5

    def calcular_salario_semanal(self):
        # Salario semanal a partir del mensual
        return (self.salario_mensual / 30) * 7

    def calcular_salario_por_hora(self):
        # Salario por hora a partir del salario semanal
        return self.calcular_salario_semanal() / 44

    def calcular_aguinaldo_anual(self):
        return (self.salario_mensual / 30) * AGUINALDO_DIAS

    def calcular_vacaciones_anual(self):
        return (self.salario_mensual / 30) * VACACIONES_DIAS

    def calcular_afp(self):
        # AFP sobre salario mensual más vacaciones mensuales
        return (self.salario_mensual + (self.calcular_vacaciones_anual() / 12)) * AFP

    def calcular_seguro_social(self):
        # Seguro Social sobre salario mensual más vacaciones mensuales
        return (self.salario_mensual + (self.calcular_vacaciones_anual() / 12)) * SEGURO_SOCIAL

    def calcular_icaf(self):
        # ICAF sobre salario mensual más vacaciones mensuales
        return (self.salario_mensual + (self.calcular_vacaciones_anual() / 12)) * ICAF

    def calcular_salario_total_mensual(self):
        # Salario total considerando beneficios
        return (self.salario_mensual + 
                (self.calcular_aguinaldo_anual() / 12) + 
                (self.calcular_vacaciones_anual() / 12) +
                self.calcular_afp() + 
                self.calcular_seguro_social() + 
                self.calcular_icaf())

    def calcular_salario_total_por_cantidad(self):
        # Total salario mensual por la cantidad de empleados
        return self.calcular_salario_total_mensual() * self.cantidad_empleados

    def __str__(self):
        return f"{self.nombre_puesto} - Salario: {self.salario_mensual} - Cantidad: {self.cantidad_empleados}"


class Proyecto(models.Model):
    id_proyecto = models.DecimalField(max_digits=10, decimal_places=2, unique=True)  # ID decimal para el proyecto
    nombre_proyecto = models.CharField(max_length=200)
    cd = models.ManyToManyField(CostosDirectos, related_name='proyectos')
    ci = models.ManyToManyField(CostosIndirectos, related_name='proyectos')
    duracion = models.FloatField()  # Duración en meses
    total_cd = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    total_ci = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    esfuerzo = models.FloatField()  # Esfuerzo estimado en horas/persona
    productividad = models.FloatField()  # Productividad en puntos de función/persona
    punto_de_funcion = models.FloatField()  # Puntos de función del proyecto
    total_empleado = models.IntegerField()  # Total de empleados asignados

    # (Los métodos del modelo siguen siendo los mismos...)

    def __str__(self):
        return f"Proyecto {self.id_proyecto} - {self.nombre_proyecto}"
    
