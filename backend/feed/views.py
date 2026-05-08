from django.db.models import Q
from rest_framework import generics

from accounts.models import Friendship
from feed.models import Activity
from feed.serializers import ActivitySerializer


class FeedView(generics.ListAPIView):
	serializer_class = ActivitySerializer

	def get_queryset(self):
		user = self.request.user
		friend_ids = Friendship.objects.filter(
			Q(from_user=user) | Q(to_user=user),
			status=Friendship.Status.ACCEPTED,
		).values_list(
			"from_user_id", "to_user_id"
		)

		ids = set()
		for from_id, to_id in friend_ids:
			ids.add(from_id)
			ids.add(to_id)
		ids.discard(user.id)

		return (
			Activity.objects.filter(actor_id__in=ids)
			.select_related(
				"actor__profile",
				"target_user__profile",
				"pin__restaurant",
			)
			.prefetch_related("pin__personas", "pin__restaurant__cuisines")
		)
