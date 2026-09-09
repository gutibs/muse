"""El perfil propio, el ajeno y los pins de alguien."""

import logging

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response

from accounts.models import DietaryPreference
from accounts.serializers import (
	AccountDeletionSerializer,
	DietaryPreferenceSerializer,
	ForeignProfileSerializer,
	ProfileSerializer,
)
from accounts.services.account_deletion import anonymise_user
from accounts.services.visibility import require_can_view
from pins.selectors import visible_pins
from pins.serializers import PinSerializer

logger = logging.getLogger(__name__)

User = get_user_model()


class ProfileView(generics.RetrieveUpdateDestroyAPIView):
	serializer_class = ProfileSerializer

	def get_object(self):
		return self.request.user.profile

	def destroy(self, request, *args, **kwargs):
		"""Right to erasure. Anonymises rather than dropping the row — see
		accounts.services.account_deletion and docs/PRODUCT_DECISIONS.md D-009.
		"""
		serializer = AccountDeletionSerializer(data=request.data, context={"request": request})
		serializer.is_valid(raise_exception=True)
		anonymise_user(request.user)
		return Response(status=status.HTTP_204_NO_CONTENT)


class DietaryPreferenceListView(generics.ListAPIView):
	"""Read-only list of available dietary preferences. Rows are seeded by
	migration; not user-creatable. Frontend uses this to populate the
	multi-select on the profile edit screen."""

	serializer_class = DietaryPreferenceSerializer
	queryset = DietaryPreference.objects.all()
	pagination_class = None


class PublicProfileView(generics.RetrieveAPIView):
	# ForeignProfileSerializer y no ProfileSerializer: el permiso de abajo
	# decide a quién podés mirar, no qué campos suyos ves. Ver el docstring
	# del serializer.
	serializer_class = ForeignProfileSerializer

	def get_object(self):
		user = get_object_or_404(
			User.objects.select_related("profile"),
			pk=self.kwargs["user_id"],
		)
		require_can_view(self.request.user, user)
		return user.profile


class UserPinsView(generics.ListAPIView):
	serializer_class = PinSerializer
	pagination_class = None

	def get_queryset(self):
		user = get_object_or_404(User, pk=self.kwargs["user_id"])
		require_can_view(self.request.user, user)
		# Through the shared selector so `?status=all` means the same thing
		# here as it does on /pins/ — it used to be passed through as a
		# literal status and returned nothing.
		return visible_pins(
			self.request.user,
			owner=user,
			status=self.request.query_params.get("status"),
		)
