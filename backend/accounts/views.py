from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from accounts.models import Friendship
from accounts.serializers import (
	ChangePasswordSerializer,
	EmailInvitationSerializer,
	FriendshipSerializer,
	ProfileSerializer,
	RegisterSerializer,
	UserPublicSerializer,
)
from pins.models import Pin
from pins.serializers import PinSerializer

User = get_user_model()


def _are_friends(user_a, user_b) -> bool:
	if user_a == user_b:
		return True
	return Friendship.objects.filter(
		(Q(from_user=user_a, to_user=user_b) | Q(from_user=user_b, to_user=user_a)),
		status=Friendship.Status.ACCEPTED,
	).exists()


class RegisterView(generics.CreateAPIView):
	serializer_class = RegisterSerializer
	permission_classes = (permissions.AllowAny,)

	def create(self, request, *args, **kwargs):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		result = serializer.save()
		return Response(result, status=status.HTTP_201_CREATED)


class ProfileView(generics.RetrieveUpdateAPIView):
	serializer_class = ProfileSerializer

	def get_object(self):
		return self.request.user.profile


class ChangePasswordView(generics.GenericAPIView):
	serializer_class = ChangePasswordSerializer

	def post(self, request):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		request.user.set_password(serializer.validated_data["new_password"])
		request.user.save()
		return Response(status=status.HTTP_204_NO_CONTENT)


class UserSearchView(generics.ListAPIView):
	serializer_class = UserPublicSerializer

	def get_queryset(self):
		query = self.request.query_params.get("q", "").strip()
		if not query or len(query) < 2:
			return User.objects.none()

		# Match by email OR display name. We query the two conditions
		# separately and union the ids to avoid JOIN quirks that can hide
		# users who don't have a Profile row yet.
		email_ids = User.objects.filter(email__icontains=query).values_list("id", flat=True)
		name_ids = User.objects.filter(
			profile__display_name__icontains=query
		).values_list("id", flat=True)
		matching_ids = set(email_ids) | set(name_ids)
		matching_ids.discard(self.request.user.id)

		return User.objects.filter(id__in=matching_ids).select_related("profile")[:20]


class FriendshipViewSet(viewsets.ModelViewSet):
	serializer_class = FriendshipSerializer
	http_method_names = ["get", "post", "patch", "delete"]

	def get_queryset(self):
		user = self.request.user
		return Friendship.objects.filter(
			Q(from_user=user) | Q(to_user=user)
		).select_related("from_user__profile", "to_user__profile")

	def partial_update(self, request, *args, **kwargs):
		instance = self.get_object()
		# Only the recipient can accept/decline
		if instance.to_user != request.user:
			return Response(
				{"detail": "Only the recipient can respond to a friend request."},
				status=status.HTTP_403_FORBIDDEN,
			)
		new_status = request.data.get("status")
		if new_status not in (Friendship.Status.ACCEPTED, Friendship.Status.DECLINED):
			return Response(
				{"detail": "status must be 'accepted' or 'declined'."},
				status=status.HTTP_400_BAD_REQUEST,
			)
		instance.status = new_status
		instance.save(update_fields=["status", "updated_at"])
		return Response(self.get_serializer(instance).data)

	@action(detail=False, methods=["get"])
	def requests(self, request):
		"""Pending requests received by the current user."""
		qs = Friendship.objects.filter(
			to_user=request.user, status=Friendship.Status.PENDING
		).select_related("from_user__profile", "to_user__profile")
		serializer = self.get_serializer(qs, many=True)
		return Response(serializer.data)

	@action(detail=False, methods=["get"])
	def friends(self, request):
		"""Accepted friendships for the current user."""
		qs = Friendship.objects.filter(
			Q(from_user=request.user) | Q(to_user=request.user),
			status=Friendship.Status.ACCEPTED,
		).select_related("from_user__profile", "to_user__profile")
		serializer = self.get_serializer(qs, many=True)
		return Response(serializer.data)


class EmailInvitationView(generics.CreateAPIView):
	serializer_class = EmailInvitationSerializer


class PublicProfileView(generics.RetrieveAPIView):
	serializer_class = ProfileSerializer

	def get_object(self):
		user = get_object_or_404(
			User.objects.select_related("profile"),
			pk=self.kwargs["user_id"],
		)
		if not _are_friends(self.request.user, user):
			raise PermissionDenied("You are not friends with this user.")
		return user.profile


class UserPinsView(generics.ListAPIView):
	serializer_class = PinSerializer
	pagination_class = None

	def get_queryset(self):
		user = get_object_or_404(User, pk=self.kwargs["user_id"])
		if not _are_friends(self.request.user, user):
			raise PermissionDenied("You are not friends with this user.")

		qs = (
			Pin.objects.filter(user=user)
			.select_related("restaurant", "restaurant__cuisine")
			.prefetch_related("personas")
		)
		status_param = self.request.query_params.get("status")
		if status_param:
			qs = qs.filter(status=status_param)
		return qs
