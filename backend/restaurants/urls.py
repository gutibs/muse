from rest_framework.routers import DefaultRouter

from restaurants.views import CuisineViewSet, RestaurantViewSet, TagViewSet

router = DefaultRouter()
router.register(r"restaurants", RestaurantViewSet, basename="restaurant")
router.register(r"cuisines", CuisineViewSet, basename="cuisine")
router.register(r"tags", TagViewSet, basename="tag")

urlpatterns = router.urls
