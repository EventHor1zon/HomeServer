from django.urls import re_path
from . import consumers


# stream_path = "ws/" + consumers.API_WEBSOCKET_INCOMMING_STREAM_EXTENSION 

websocket_urlpatterns = [
    re_path('ws/peripheral/', consumers.CommandConsumer.as_asgi()),
    re_path('ws/discover/', consumers.Discoverer.as_asgi()),
    re_path('ws/ledctrl', consumers.LedCtrlConsumer.as_asgi()),
    re_path('ws/stream/', consumers.DeviceStream.as_asgi()),
]