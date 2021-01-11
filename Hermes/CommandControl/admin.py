from django.contrib import admin

# Register your models here.

from django.contrib import admin

from .models import Device, Peripheral, Parameter

admin.site.register(Device)
admin.site.register(Peripheral)
admin.site.register(Parameter)