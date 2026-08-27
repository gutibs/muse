from django.db.models import Q
from rest_framework import generics

from accounts.services.visibility import (
	visible_friend_and_blocked_ids,
	visible_pin_filter,
)
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
			# F2.A: la actividad de un pin que pasó a privado desaparece,
			# aunque haya ocurrido cuando era visible. `pin__isnull` no es
			# opcional — la actividad de amistad no cuelga de ningún pin y sin
			# esa rama se iría media pantalla con ella.
			.filter(Q(pin__isnull=True) | visible_pin_filter(self.request.user, prefix="pin__"))
			.select_related(
				"actor__profile",
				"target_user__profile",
				"pin__restaurant",
			)
			.prefetch_related("pin__tags", "pin__restaurant__cuisines")
		)
