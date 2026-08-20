from rest_framework import generics

from accounts.services.friendships import friend_ids
from feed.models import Activity
from feed.serializers import ActivitySerializer


class FeedView(generics.ListAPIView):
	serializer_class = ActivitySerializer

	def get_queryset(self):
		ids = friend_ids(self.request.user)

		return (
			Activity.objects.filter(actor_id__in=ids)
			.select_related(
				"actor__profile",
				"target_user__profile",
				"pin__restaurant",
			)
			.prefetch_related("pin__tags", "pin__restaurant__cuisines")
		)
