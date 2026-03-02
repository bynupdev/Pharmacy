from django.contrib import admin
from prescriptions.models import Prescription, PrescriptionItem

# Register your models here.
admin.site.register(Prescription)
admin.site.register(PrescriptionItem)
