from django.contrib import admin
from inventory.models import Supplier, Drug, Batch

# Register your models here.
admin.site.register(Supplier)
admin.site.register(Drug)
admin.site.register(Batch)
