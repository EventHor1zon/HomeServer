from django.shortcuts import render, get_object_or_404

# Create your views here.

from django.http import HttpResponse
from django.template import loader
from .models import Device, Peripheral, Parameter
from django.views.generic import TemplateView, DetailView
from Hermes.settings import DATABASES

import os
import subprocess
import json

def get_uptime():
    p = subprocess.Popen(["uptime", "-p"], stdout=subprocess.PIPE)
    output = p.stdout.read()
    return output.decode("utf-8")

def index(request):
    devices = Device.objects.order_by('id')
    server_ip = request.get_host()
    server_ut = get_uptime()
    template=  loader.get_template("CC/index.html")
    context = {
        "devices": devices,
        "ip": server_ip,
        "connected_devices": len(devices),
        "db_type": DATABASES['default']['ENGINE'].split(".")[-1],
        "uptime": server_ut
    }
    return HttpResponse(template.render(context, request))


class DeviceView(DetailView):

    template_name = "CC/device_details.html"
    model = Device

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['devices'] = Device.objects.all()
        return context


class PeripheralView(DetailView):

    template_name = "CC/peripheral_detail.html"
    model = Peripheral

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['devices'] = Device.objects.all()
        context['device'] = self.model.device
        return context



def device_details(request, device_id):
    device = get_object_or_404(Device, pk=device_id)
    template=  loader.get_template("CC/device_details.html")
    context = {
        "device": device,
    }
    return HttpResponse(template.render(context, request))


def peripheral_details(request):
    return HttpResponse("Hi")

