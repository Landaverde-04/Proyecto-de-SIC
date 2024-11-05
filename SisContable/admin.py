from django.contrib import admin
from .models import CostoDirecto, Cuenta, CostoIndirecto


admin.site.register(CostoDirecto)
admin.site.register(Cuenta)
admin.site.register(CostoIndirecto)
