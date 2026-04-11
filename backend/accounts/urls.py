from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.views import (
	ChangePasswordView,
	EmailInvitationView,
	FriendshipViewSet,
	ProfileView,
	RegisterView,
	UserSearchView,
)

router = DefaultRouter()
router.register("friendships", FriendshipViewSet, basename="friendship")

urlpatterns = [
	path("register/", RegisterView.as_view(), name="register"),
	path("token/", TokenObtainPairView.as_view(), name="token_obtain"),
	path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
	path("profile/", ProfileView.as_view(), name="profile"),
	path("change-password/", ChangePasswordView.as_view(), name="change_password"),
	path("search/", UserSearchView.as_view(), name="user_search"),
	path("invite/", EmailInvitationView.as_view(), name="email_invite"),
	path("", include(router.urls)),
]
