from decimal import Decimal
from datetime import date
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

class PeriodoContable(models.Model):
    año = models.IntegerField(unique=True)
    inicio = models.DateField()
    fin = models.DateField()
    cerrado = models.BooleanField(default=False)  # Indica si el periodo está cerrado

    @classmethod
    def crear_periodo_anual(cls, año):
        """Crea o recupera un periodo contable anual para el año dado."""
        inicio = date(año, 1, 1)
        fin = date(año, 12, 31)
        periodo, creado = cls.objects.get_or_create(año=año, defaults={'inicio': inicio, 'fin': fin})
        return periodo

    def __str__(self):
        return f"Periodo {self.año} - Del {self.inicio} al {self.fin}"

    def calcular_estado_de_resultados(self):
        """Calcula la utilidad o pérdida bruta y crea un movimiento con el resultado."""
        if self.cerrado:
            return "El periodo ya está cerrado, no se puede recalcular el estado de resultados."

        # Calcular ingresos (cuentas que empiezan con '5') en el periodo
        ingresos = Movimiento.objects.filter(
            transaccion__periodo_contable=self,  # Movimientos del periodo actual
            cuenta__codigo__startswith='5'       # Cuentas de ingresos
        ).aggregate(total=Sum('haber'))['total'] or 0

        # Calcular costos (cuentas que empiezan con '4') en el periodo
        costos = Movimiento.objects.filter(
            transaccion__periodo_contable=self,  # Movimientos del periodo actual
            cuenta__codigo__startswith='4'       # Cuentas de costos
        ).aggregate(total=Sum('debe'))['total'] or 0

        utilidad_bruta = ingresos - costos  # Utilidad si es positivo, pérdida si es negativo

        # Crear un movimiento para registrar la utilidad o pérdida bruta
        cuenta_utilidad = Cuenta.objects.get(codigo="3301")  # Cuenta para utilidad o pérdida bruta
        movimiento_utilidad = Movimiento.objects.create(
            transaccion=None,  # No está ligado a una transacción específica, sino al periodo
            cuenta=cuenta_utilidad,
            debe=abs(utilidad_bruta) if utilidad_bruta < 0 else 0,
            haber=utilidad_bruta if utilidad_bruta > 0 else 0
        )

        # Asociar el movimiento al periodo contable
        movimiento_utilidad.transaccion = None
        movimiento_utilidad.save()

        return utilidad_bruta  # Retorna el valor para usar en el HTML


class Transaccion(models.Model):
    id_transaccion = models.AutoField(primary_key=True)
    fecha = models.DateField()
    periodo_contable = models.ForeignKey(PeriodoContable, on_delete=models.PROTECT, related_name="transacciones")

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
    transaccion = models.ForeignKey(Transaccion, on_delete=models.CASCADE, related_name="movimientos", null=True, blank=True)
    cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE)
    debe = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    haber = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    periodo_contable = models.ForeignKey(PeriodoContable, on_delete=models.PROTECT, related_name="movimientos")

    def __str__(self):
        return f"Cuenta {self.cuenta.codigo}: Debe {self.debe}, Haber {self.haber}"

class CostoDirecto(models.Model):
    nombre = models.CharField(max_length=100)
    salario_mensual = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_empleados = models.PositiveIntegerField(default=1)

    # Porcentajes fijos como Decimal
    PORCENTAJE_ISSS = Decimal('0.075')
    PORCENTAJE_AFP = Decimal('0.0775')
    PORCENTAJE_INCAF = Decimal('0.01')

    @property
    def isss(self):
        return self.salario_mensual * self.PORCENTAJE_ISSS

    @property
    def afp(self):
        return self.salario_mensual * self.PORCENTAJE_AFP

    @property
    def vacaciones(self):
        # Convertimos 0.30 y 12 a Decimal para asegurar consistencia en el tipo
        return ((self.salario_mensual / 2) + (self.salario_mensual / 2) * Decimal('0.30')) / Decimal('12')

    @property
    def aguinaldo(self):
        # Convertimos 30 y 19 a Decimal para asegurar consistencia en el tipo
        return ((self.salario_mensual / Decimal('30')) * Decimal('19')) / Decimal('12')

    @property
    def incaf(self):
        return self.salario_mensual * self.PORCENTAJE_INCAF

    @property
    def total_con_prestaciones(self):
        # Calcula el salario total mensual con todas las prestaciones
        total_prestaciones = (
            self.salario_mensual + self.isss + self.afp + self.vacaciones + self.aguinaldo + self.incaf
        )
        return total_prestaciones * self.cantidad_empleados

    def __str__(self):
        return self.nombre


class CostoIndirecto(models.Model):
    """Catálogo de costos indirectos"""
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    monto = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.nombre} - ${self.monto}"


class Proyecto(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    puntos_funcion_total = models.PositiveIntegerField(help_text="Total de puntos de función del proyecto")
    productividad = models.DecimalField(max_digits=5, decimal_places=2, help_text="Puntos de función por persona-hora")
    
    # Relaciones con los costos directos e indirectos
    costos_directos = models.ManyToManyField('CostoDirecto', blank=True, related_name="proyectos_directos")
    costos_indirectos = models.ManyToManyField('CostoIndirecto', blank=True, related_name="proyectos_indirectos")

    # Campos calculados
    duracion_total = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Duración en meses")
    esfuerzo_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Esfuerzo total en horas/persona")
    costo_total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Costo total del proyecto")

    def calcular_esfuerzo_total(self):
        """Calcula el esfuerzo total del proyecto en horas/persona basado en puntos de función y productividad."""
        if self.productividad > 0:
            self.esfuerzo_total = Decimal(self.puntos_funcion_total) / self.productividad
            self.save()
        else:
            self.esfuerzo_total = Decimal('0')
        return self.esfuerzo_total

    def calcular_total_empleados(self):
        """Calcula el total de empleados sumando la cantidad de empleados en los costos directos asociados al proyecto."""
        total_empleados = sum(costo_directo.cantidad_empleados for costo_directo in self.costos_directos.all())
        print(f"Total de empleados calculado: {total_empleados}")  # Depuración
        return total_empleados

    def calcular_duracion_total(self):
        """Calcula la duración total del proyecto en meses, dividiendo el esfuerzo total entre el número de empleados."""
        total_empleados = self.calcular_total_empleados()
        if total_empleados > 0 and self.esfuerzo_total > 0:
            # 160 asume 160 horas laborales en un mes
            self.duracion_total = self.esfuerzo_total / Decimal(total_empleados) 
            print(f"Duración total calculada: {self.duracion_total}")  # Depuración
            self.save()
        else:
            self.duracion_total = Decimal('0')
            print("Duración total establecida en 0 debido a total_empleados o esfuerzo_total siendo 0")  # Depuración
        return self.duracion_total

    def calcular_total_salarios_cd(self):
        """Calcula el total de salarios de los costos directos asociados al proyecto por mes."""
        return sum(cd.total_con_prestaciones for cd in self.costos_directos.all())

    def calcular_total_costos_directos(self):
        """Calcula el total de costos directos (CDtotal) para la duración del proyecto."""
        if self.duracion_total:
            return self.calcular_total_salarios_cd() * self.duracion_total
        return Decimal('0')

    def calcular_total_costos_indirectos(self):
        """Calcula el total de costos indirectos (CItotal) para la duración del proyecto."""
        total_indirectos = sum(ci.monto for ci in self.costos_indirectos.all())
        if self.duracion_total:
            return total_indirectos * self.duracion_total
        return Decimal('0')

    def calcular_costo_total(self):
        """Calcula el costo total del proyecto como la suma de costos directos e indirectos."""
        CDtotal = self.calcular_total_costos_directos()
        CItotal = self.calcular_total_costos_indirectos()
        self.costo_total = CDtotal + CItotal
        self.save()
        return self.costo_total

    def __str__(self):
        return self.nombre