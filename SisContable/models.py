from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Sum

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


class CostosIndirectos(models.Model):
    nombre_costo = models.CharField(max_length=100)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    cuenta_asociada = models.ForeignKey(Cuenta, null=True, blank=True, on_delete=models.SET_NULL)

    # Método para calcular el costo diario (monto / 30).
    def calcular_costo_diario(self):
        if self.monto > 0:
            return self.monto / 30
        return 0.00  # Si no se especificó monto, devolver 0.

    # Método para calcular el costo semanal (costo diario * 7).
    def calcular_costo_semanal(self):
        costo_diario = self.calcular_costo_diario()
        if costo_diario > 0:
            return costo_diario * 7
        return 0.00  # Si no se puede calcular el costo diario, devolver 0.

    # Método para calcular el costo por hora (costo semanal / 44).
    def calcular_costo_por_hora(self):
        costo_semanal = self.calcular_costo_semanal()
        if costo_semanal > 0:
            return costo_semanal / 44
        return 0.00  # Si no se puede calcular el costo semanal, devolver 0.

    def __str__(self):
        return f"{self.nombre_costo} - Monto: {self.monto}"

class Puesto(models.Model):
    nombre_puesto = models.CharField(max_length=100)
    salario_puesto = models.DecimalField(max_digits=12, decimal_places=2)
    cantidad = models.IntegerField(default=1)
    salarios = models.ForeignKey(Cuenta, null=True, blank=True, on_delete=models.SET_NULL)

    # Método para calcular el salario diario (salario / 30).
    def calcular_salario_diario(self):
        return self.salario_puesto / 30

    # Método para calcular el salario semanal (salario diario * 7).
    def calcular_salario_semanal(self):
        return self.calcular_salario_diario() * 7

    # Método para calcular el salario por hora (salario semanal / 44).
    def calcular_salario_por_hora(self):
        return self.calcular_salario_semanal() / 44

    # Método para calcular el aguinaldo anual (salario diario * 25).
    def calcular_aguinaldo_anual(self):
        return self.calcular_salario_diario() * 25

    # Método para calcular el aguinaldo mensual (aguinaldo anual / 12).
    def calcular_aguinaldo_mensual(self):
        return self.calcular_aguinaldo_anual() / 12

    # Método para calcular las vacaciones anuales ((salario diario * 25) * 1.40).
    def calcular_vacaciones_anual(self):
        return (self.calcular_salario_diario() * 25) * 1.40

    # Método para calcular las vacaciones mensuales (vacaciones anuales / 12).
    def calcular_vacaciones_mensual(self):
        return self.calcular_vacaciones_anual() / 12

    # Método para calcular el AFP (salario mensual + vacaciones mensual) * 0.0775.
    def calcular_afp(self):
        salario_mensual = self.salario_puesto
        vacaciones_mensual = self.calcular_vacaciones_mensual()
        return (salario_mensual + vacaciones_mensual) * 0.0775

    # Método para calcular el Seguro Social (salario mensual + vacaciones mensual) * 0.075.
    def calcular_seguro_social(self):
        salario_mensual = self.salario_puesto
        vacaciones_mensual = self.calcular_vacaciones_mensual()
        return (salario_mensual + vacaciones_mensual) * 0.075

    # Método para calcular el ICAF (salario mensual + vacaciones mensual) * 0.01.
    def calcular_icaf(self):
        salario_mensual = self.salario_puesto
        vacaciones_mensual = self.calcular_vacaciones_mensual()
        return (salario_mensual + vacaciones_mensual) * 0.01

    # Método para calcular el salario total mensual.
    # Salario total mensual = salario mensual + aguinaldo mensual + vacaciones mensual + AFP + Seguro + ICAF.
    def calcular_salario_total_mensual(self):
        salario_mensual = self.salario_puesto
        aguinaldo_mensual = self.calcular_aguinaldo_mensual()
        vacaciones_mensual = self.calcular_vacaciones_mensual()
        afp = self.calcular_afp()
        seguro_social = self.calcular_seguro_social()
        icaf = self.calcular_icaf()

        return salario_mensual + aguinaldo_mensual + vacaciones_mensual + afp + seguro_social + icaf

    # Método para calcular el salario total considerando la cantidad de puestos.
    def calcular_salario_total_por_cantidad(self):
        return self.calcular_salario_total_mensual() * self.cantidad

    def __str__(self):
        return f"{self.nombre_puesto} - Salario: {self.salario_puesto} - Cantidad: {self.cantidad}"