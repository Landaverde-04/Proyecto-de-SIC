from django.contrib import admin
from .models import CostosDirectos, Cuenta, CostosIndirectos


admin.site.register(CostosDirectos)
admin.site.register(Cuenta)
admin.site.register(CostosIndirectos)
