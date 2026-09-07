from django.urls import path

from imports.views import ImportJobConfirmView, ImportJobDetailView, ImportJobListView

urlpatterns = [
	path("imports/", ImportJobListView.as_view(), name="import-list"),
	path("imports/<int:pk>/", ImportJobDetailView.as_view(), name="import-detail"),
	path("imports/<int:pk>/confirm/", ImportJobConfirmView.as_view(), name="import-confirm"),
]
