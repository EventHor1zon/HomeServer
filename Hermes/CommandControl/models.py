from django.db import models

# Create your models here.

from django.db import models
from datetime import datetime

class Device(models.Model):

    dev_id = models.IntegerField()
    ip_address = models.GenericIPAddressField()
    api_port = models.IntegerField(default=80)
    cmd_url = models.CharField(max_length=50)
    mac_address = models.CharField(max_length=17)
    name = models.CharField(max_length=40)
    num_peripherals = models.IntegerField()
    dev_type = models.CharField(max_length=40)
    image = models.ImageField(upload_to='CC/images/')
    sleep_state = models.IntegerField()
    is_powered = models.BooleanField(default=False)
    last_polled = models.DateField(default=datetime.min)
    setup_date = models.DateField(default=datetime.min)


class Peripheral(models.Model):

    periph_id = models.IntegerField()
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    name = models.CharField(max_length=40)
    num_params = models.IntegerField(default=0)
    periph_type = models.IntegerField(default=0)
    periph_image = models.ImageField(upload_to='CC/images/')
    sleep_state = models.IntegerField(default=0)
    is_powered = models.BooleanField(default=False)


class Parameter(models.Model):

    param_id = models.IntegerField()
    peripheral = models.ForeignKey(Peripheral, on_delete=models.CASCADE)
    name = models.CharField(max_length=40)
    max_value = models.IntegerField(default=0)
    data_type = models.IntegerField(default=0)
    is_getable = models.BooleanField(default=False)
    is_setable = models.BooleanField(default=False)
    is_action = models.BooleanField(default=False)
    last_value = models.IntegerField(default=0)
    units = models.TextField(max_length=20)


