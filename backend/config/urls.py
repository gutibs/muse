from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
	path("admin/", admin.site.urls),
	path("api/v1/auth/", include("accounts.urls")),
	path("api/v1/", include("restaurants.urls")),
	path("api/v1/", include("pins.urls")),
	path("api/v1/", include("feed.urls")),
	path("api/v1/", include("places.urls")),
]

if settings.DEBUG:
	urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
