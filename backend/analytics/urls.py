from django.urls import path

from analytics.views import EventIngestView

urlpatterns = [
	path("analytics/events/", EventIngestView.as_view(), name="analytics-events"),
]
