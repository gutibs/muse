"""Los serializers de `accounts`, por dominio.

Era un archivo de 570 líneas con quince clases: el perfil, el alta, las
contraseñas, el grafo social y la moderación, todo junto. Se parte por dominio
y este `__init__` reexporta, así que `from accounts.serializers import X` sigue
funcionando igual que antes.

**Ojo al parchear en tests**: `@patch("accounts.serializers.send_welcome_email")`
apunta al alias de acá, no al que usa el código. Los mocks van contra el módulo
donde vive quien lo llama, por ejemplo `accounts.serializers.auth`.
"""

from accounts.serializers.auth import (
	AccountDeletionSerializer,
	ChangePasswordSerializer,
	PasswordResetConfirmSerializer,
	PasswordResetRequestSerializer,
	RegisterSerializer,
)
from accounts.serializers.moderation import (
	BlockCreateSerializer,
	BlockSerializer,
	ReportSerializer,
)
from accounts.serializers.profile import (
	DietaryPreferenceSerializer,
	ForeignProfileSerializer,
	ProfileSerializer,
)
from accounts.serializers.social import (
	EmailInvitationSerializer,
	FriendshipSerializer,
	UserAnonymousSafeSerializer,
	UserPublicSerializer,
)

__all__ = [
	"AccountDeletionSerializer",
	"BlockCreateSerializer",
	"BlockSerializer",
	"ChangePasswordSerializer",
	"DietaryPreferenceSerializer",
	"EmailInvitationSerializer",
	"ForeignProfileSerializer",
	"FriendshipSerializer",
	"PasswordResetConfirmSerializer",
	"PasswordResetRequestSerializer",
	"ProfileSerializer",
	"RegisterSerializer",
	"ReportSerializer",
	"UserAnonymousSafeSerializer",
	"UserPublicSerializer",
]
