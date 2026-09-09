"""Las vistas de `accounts`, por dominio.

Era un archivo de 482 líneas con catorce vistas, nueve throttles y dos
símbolos sueltos. Se parte por dominio y este `__init__` reexporta, así que
`accounts/urls.py` y los tests que importan de acá siguen funcionando.
"""

from accounts.views.auth import (
	PASSWORD_RESET_ACCEPTED,
	ChangePasswordView,
	ConsentView,
	PasswordResetConfirmView,
	PasswordResetView,
	RegisterView,
)
from accounts.views.moderation import (
	BlockViewSet,
	ReportCreateView,
)
from accounts.views.profile import (
	DietaryPreferenceListView,
	ProfileView,
	PublicProfileView,
	UserPinsView,
)
from accounts.views.social import (
	EmailInvitationView,
	FriendCodeRedeemView,
	FriendCodeRotateView,
	FriendshipViewSet,
	UserSearchView,
	_are_friends,
)
from accounts.views.throttles import (
	ClientIPRateThrottle,
	FriendCodeThrottle,
	InviteThrottle,
	LoginAnonThrottle,
	LoginUserThrottle,
	PasswordResetConfirmThrottle,
	PasswordResetThrottle,
	RegisterAnonThrottle,
	ReportThrottle,
	UserSearchThrottle,
)

__all__ = [
	"FriendCodeRedeemView",
	"FriendCodeThrottle",
	"FriendCodeRotateView",
	"PASSWORD_RESET_ACCEPTED",
	"_are_friends",
	"BlockViewSet",
	"ChangePasswordView",
	"ClientIPRateThrottle",
	"ConsentView",
	"DietaryPreferenceListView",
	"EmailInvitationView",
	"FriendshipViewSet",
	"InviteThrottle",
	"LoginAnonThrottle",
	"LoginUserThrottle",
	"PasswordResetConfirmThrottle",
	"PasswordResetConfirmView",
	"PasswordResetThrottle",
	"PasswordResetView",
	"ProfileView",
	"PublicProfileView",
	"RegisterAnonThrottle",
	"RegisterView",
	"ReportCreateView",
	"ReportThrottle",
	"UserPinsView",
	"UserSearchThrottle",
	"UserSearchView",
]
