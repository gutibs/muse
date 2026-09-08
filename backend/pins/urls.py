from django.urls import path
from rest_framework.routers import DefaultRouter

from pins.views import PinViewSet, SharedListPublicView, SharedListViewSet
from pins.views_public import ShortlistVoteDetailView, ShortlistVoteView

router = DefaultRouter()
router.register(r"pins", PinViewSet, basename="pin")
router.register(r"shared-lists", SharedListViewSet, basename="shared-list")

urlpatterns = [
	path("shared/<uuid:token>/", SharedListPublicView.as_view(), name="shared-list-public"),
	path("shared/<uuid:token>/votes/", ShortlistVoteView.as_view(), name="shortlist-votes"),
	path(
		"shared/<uuid:token>/votes/<int:item_id>/",
		ShortlistVoteDetailView.as_view(),
		name="shortlist-vote-detail",
	),
	*router.urls,
]
