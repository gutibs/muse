from rest_framework import generics

from accounts.services.visibility import visible_friend_and_blocked_ids
from feed.models import Activity
from feed.serializers import ActivitySerializer


class FeedView(generics.ListAPIView):
	serializer_class = ActivitySerializer

	def get_queryset(self):
		ids, hidden = visible_friend_and_blocked_ids(self.request.user)

		return (
			Activity.objects.filter(actor_id__in=ids)
			# El `target_user` no se filtraba: la actividad de amistad de un
			# amigo tuyo con alguien que bloqueaste te lo mostraba igual.
			.exclude(target_user_id__in=hidden)
			.select_related(
				"actor__profile",
				"target_user__profile",
				"pin__restaurant",
			)
			.prefetch_related("pin__tags", "pin__restaurant__cuisines")
		)
