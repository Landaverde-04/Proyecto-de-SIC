from django.db import models

#modelo para las categorias del catalogo de cuentas
class Categoria(models.Model):
    codigo_categoria = models.IntegerField(primary_key=True)
    nombre_categoria = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre_categoria
#Modelo para el catalogo de cuentas
class Cuentas(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.CharField(max_length=100)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre
    
#Modelo para transaccion    
class Transaccion(models.Model):
    fecha = models.DateField(auto_now_add=True)
    monto_total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Transacción {self.id} - {self.fecha}"

# Asociacion entre tarnsaccion y cuentas
class CuentaTransaccion(models.Model):
    transaccion = models.ForeignKey(Transaccion, on_delete=models.CASCADE)
    cuenta = models.ForeignKey(Cuentas, on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Transacción {self.transaccion.id} - Cuenta {self.cuenta.nombre} - Monto {self.monto}"

