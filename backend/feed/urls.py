from django.urls import path

from feed.views import FeedView

urlpatterns = [
	path("feed/", FeedView.as_view(), name="feed"),
]
