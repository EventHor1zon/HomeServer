from django.shortcuts import render, get_object_or_404

# Create your views here.

from django.http import HttpResponse
from django.template import loader
from .models import Device, Peripheral, Parameter
from django.views.generic import TemplateView, DetailView, View
from Hermes.settings import DATABASES

import os
import subprocess
import json
from . import command_api as CA

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



class DiscoverView(View):


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get(self, request):

        template = loader.get_template("CC/discover.html")
        devices = Device.objects.all()

        context = {
            "devices": devices,
        }

        return HttpResponse(template.render(context, request))


class LedControlView(View):

    def __init__(self):
        self.control_groups = []
        super().__init__()

    def get(self, request):
        template = loader.get_template("CC/ledcontrol.html")
        
        led_periphs = Peripheral.objects.filter(periph_type=CA.PTYPE_ADDR_LEDS)
        dev_ids = [x.device.dev_id for x in led_periphs]
        led_devices = Device.objects.filter(dev_id__in=dev_ids)

        devices = Device.objects.all()

        context = {
            "devices": devices,
            "led_strips": led_periphs,
            "led_devices": led_devices,
        }

        return HttpResponse(template.render(context, request))


class StreamView(View):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    def get(self, request):
        template = loader.get_template("CC/stream.html")

        stream_params = Parameter.objects.filter(is_streamable=True)
        stream_periphs = list(set([x.peripheral for x in stream_params]))
        stream_devices = list(set([x.peripheral.device for x in stream_params]))

        context = {
            "stream_params": stream_params,
            "stream_periphs": stream_periphs,
            "stream_devices": stream_devices,
        }

        return HttpResponse(template.render(context, request))