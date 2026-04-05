from rest_framework.routers import DefaultRouter

from pins.views import PersonaViewSet, PinViewSet

router = DefaultRouter()
router.register(r"pins", PinViewSet, basename="pin")
router.register(r"personas", PersonaViewSet, basename="persona")

urlpatterns = router.urls
