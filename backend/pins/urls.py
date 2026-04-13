from django.urls import path
from rest_framework.routers import DefaultRouter

from pins.views import PersonaViewSet, PinViewSet, SharedListPublicView, SharedListViewSet

router = DefaultRouter()
router.register(r"pins", PinViewSet, basename="pin")
router.register(r"personas", PersonaViewSet, basename="persona")
router.register(r"shared-lists", SharedListViewSet, basename="shared-list")

urlpatterns = [
	path("shared/<uuid:token>/", SharedListPublicView.as_view(), name="shared-list-public"),
	*router.urls,
]
