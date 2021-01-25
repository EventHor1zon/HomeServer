
from django.urls import path

from . import views


urlpatterns = [
    path('', views.index, name="index"),
    path('device/<int:pk>/', views.DeviceView.as_view(), name="device"),
    path('peripheral/<int:pk>/', views.PeripheralView.as_view(), name="peripheral"),
    path('discover', views.DiscoverView.as_view(), name="discover"),
    path('ledcontrol', views.LedControlView.as_view(), name="ledcontrol")
]