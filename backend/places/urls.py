from django.urls import path

from places import views

urlpatterns = [
	path("places/autocomplete/", views.autocomplete, name="places-autocomplete"),
	path("places/cities/autocomplete/", views.city_autocomplete, name="places-cities-autocomplete"),
	path("places/details/<str:place_id>/", views.place_details, name="places-details"),
	path("places/photo/", views.place_photo, name="places-photo"),
	path(
		"places/reverse-geocode/", views.ReverseGeocodeView.as_view(), name="places-reverse-geocode"
	),
]
