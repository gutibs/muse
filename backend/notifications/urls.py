from django.urls import path

from notifications.views import DeviceTokenView

urlpatterns = [
	path("devices/", DeviceTokenView.as_view(), name="notification-devices"),
]
