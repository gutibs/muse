from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.views import (
	ChangePasswordView,
	DietaryPreferenceListView,
	EmailInvitationView,
	FriendshipViewSet,
	LoginAnonThrottle,
	LoginUserThrottle,
	ProfileView,
	PublicProfileView,
	RegisterView,
	UserPinsView,
	UserSearchView,
)


class ThrottledTokenObtainPairView(TokenObtainPairView):
	throttle_classes = (LoginAnonThrottle, LoginUserThrottle)


class ThrottledTokenRefreshView(TokenRefreshView):
	throttle_classes = (LoginAnonThrottle, LoginUserThrottle)


router = DefaultRouter()
router.register("friendships", FriendshipViewSet, basename="friendship")

urlpatterns = [
	path("register/", RegisterView.as_view(), name="register"),
	path("token/", ThrottledTokenObtainPairView.as_view(), name="token_obtain"),
	path("token/refresh/", ThrottledTokenRefreshView.as_view(), name="token_refresh"),
	path("profile/", ProfileView.as_view(), name="profile"),
	path("dietary-preferences/", DietaryPreferenceListView.as_view(), name="dietary_preferences"),
	path("change-password/", ChangePasswordView.as_view(), name="change_password"),
	path("search/", UserSearchView.as_view(), name="user_search"),
	path("invite/", EmailInvitationView.as_view(), name="email_invite"),
	path("users/<int:user_id>/", PublicProfileView.as_view(), name="public_profile"),
	path("users/<int:user_id>/pins/", UserPinsView.as_view(), name="user_pins"),
	path("", include(router.urls)),
]
