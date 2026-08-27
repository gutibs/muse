import logging
import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
	if DEBUG:
		SECRET_KEY = "django-insecure-dev-only-do-not-use-in-prod-" + "x" * 30
		logger.warning(
			"DJANGO_SECRET_KEY not set; using dev fallback. "
			"Set DJANGO_SECRET_KEY in .env for any non-trivial work."
		)
	else:
		raise ImproperlyConfigured(
			"DJANGO_SECRET_KEY environment variable is required in production"
		)

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Google Places API — server-side only
GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")

INSTALLED_APPS = [
	"django.contrib.admin",
	"django.contrib.auth",
	"django.contrib.contenttypes",
	"django.contrib.sessions",
	"django.contrib.messages",
	"django.contrib.staticfiles",
	"django.contrib.gis",
	# Third party
	"rest_framework",
	"corsheaders",
	"django_filters",
	# Local
	"accounts",
	"restaurants",
	"pins",
	"feed",
	"places",
	"analytics",
]

MIDDLEWARE = [
	"django.middleware.security.SecurityMiddleware",
	"django.contrib.sessions.middleware.SessionMiddleware",
	"corsheaders.middleware.CorsMiddleware",
	"django.middleware.common.CommonMiddleware",
	"django.middleware.csrf.CsrfViewMiddleware",
	"django.contrib.auth.middleware.AuthenticationMiddleware",
	"config.admin_locale.AdminEnglishLocaleMiddleware",
	"django.contrib.messages.middleware.MessageMiddleware",
	"django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
	{
		"BACKEND": "django.template.backends.django.DjangoTemplates",
		"DIRS": [BASE_DIR / "templates"],
		"APP_DIRS": True,
		"OPTIONS": {
			"context_processors": [
				"django.template.context_processors.debug",
				"django.template.context_processors.request",
				"django.contrib.auth.context_processors.auth",
				"django.contrib.messages.context_processors.messages",
			],
		},
	},
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
	"default": {
		"ENGINE": "django.contrib.gis.db.backends.postgis",
		"NAME": os.environ.get("DB_NAME", "muse"),
		"USER": os.environ.get("DB_USER", "muse"),
		"PASSWORD": os.environ.get("DB_PASSWORD", "muse_dev_password"),
		"HOST": os.environ.get("DB_HOST", "localhost"),
		"PORT": os.environ.get("DB_PORT", "5432"),
	}
}

AUTH_PASSWORD_VALIDATORS = [
	{"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
	{"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
	{"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
	{"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Argentina/Buenos_Aires"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Leading slash matters: without it Django builds relative media URLs, which
# resolve differently depending on the page they are rendered from. Part of
# why avatars did not load in prod — the other part was that nginx had no
# `location /media/` at all.
MEDIA_URL = "/media/"
# Served by nginx from the `muse_media` named volume in prod (see
# docker-compose.aws.yml). A named volume rather than object storage on
# purpose: it survives the deploy's `down` + `up -d` exactly like the Postgres
# one does, and the whole photo catalogue is a few hundred MB on a disk that
# is already paid for. S3 becomes worthwhile when there is more than one
# instance to share it between, not before.
MEDIA_ROOT = BASE_DIR / "media"

# --- Cache -----------------------------------------------------------------
# Without this Django falls back to LocMemCache, which is per-process. With
# 3 gunicorn workers that made every throttle scope count roughly three times
# its configured rate, and reset on each deploy. Redis fixes the throttles and
# is what the Google Places cache will live in.
REDIS_URL = os.environ.get("REDIS_URL", "")
if REDIS_URL:
	CACHES = {
		"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL}
	}
else:
	# Tests and any environment without Redis. Explicit rather than implicit
	# so the fallback is a visible decision.
	CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Public base of the SPA — used to build shareable links and invitations.
APP_PUBLIC_URL = os.environ.get("APP_PUBLIC_URL", "http://localhost:5174")
# Public base of this API. Separate from APP_PUBLIC_URL because in dev they
# are different origins, and because URLs built from it get persisted (see
# restaurants.services.google_place_parser.photo_url_for) — deriving them
# from the incoming request would bake that request's host into the row.
API_PUBLIC_URL = os.environ.get("API_PUBLIC_URL", "http://localhost:8001")

# Email — real SMTP in prod, console backend in dev so invitations still log output.
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Muse <no-reply@lovemuse.app>")
EMAIL_BACKEND = os.environ.get(
	"EMAIL_BACKEND",
	"django.core.mail.backends.smtp.EmailBackend"
	if not DEBUG
	else "django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") == "1"

# Resend (transactional email API). Used by accounts.services.email.send_invitation_email.
# Empty string = service raises EmailSendError(503) on send. In dev (DJANGO_DEBUG=1)
# the EMAIL_BACKEND console fallback above still works for ad-hoc Django mail.
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")

# Nominatim reverse-geocode proxy. Their usage policy
# (https://operations.osmfoundation.org/policies/nominatim/) requires a
# descriptive User-Agent identifying the app and a contact email.
APP_CONTACT_EMAIL = os.environ.get("APP_CONTACT_EMAIL", "contact@lovemuse.app")
# Adónde llegan las denuncias de contenido. Separado de APP_CONTACT_EMAIL a
# propósito: esa casilla es pública y ésta la mira quien modera.
MODERATION_EMAIL = os.environ.get("MODERATION_EMAIL", APP_CONTACT_EMAIL)
NOMINATIM_USER_AGENT = os.environ.get("NOMINATIM_USER_AGENT", "muse/1.0 (+https://lovemuse.app)")

# DRF
REST_FRAMEWORK = {
	"DEFAULT_AUTHENTICATION_CLASSES": (
		"rest_framework_simplejwt.authentication.JWTAuthentication",
	),
	"DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
	"DEFAULT_RENDERER_CLASSES": ("djangorestframework_camel_case.render.CamelCaseJSONRenderer",),
	"DEFAULT_PARSER_CLASSES": (
		"djangorestframework_camel_case.parser.CamelCaseJSONParser",
		"djangorestframework_camel_case.parser.CamelCaseFormParser",
		"djangorestframework_camel_case.parser.CamelCaseMultiPartParser",
	),
	"DEFAULT_FILTER_BACKENDS": (
		"django_filters.rest_framework.DjangoFilterBackend",
		"rest_framework.filters.SearchFilter",
		"rest_framework.filters.OrderingFilter",
	),
	"DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
	"PAGE_SIZE": 20,
	"DEFAULT_THROTTLE_CLASSES": (
		"rest_framework.throttling.AnonRateThrottle",
		"rest_framework.throttling.UserRateThrottle",
	),
	"DEFAULT_THROTTLE_RATES": {
		"anon": "60/hour",
		"user": "1000/hour",
		"login": "10/min",
		"register": "5/hour",
		"user_search": "60/hour",
		"places": "120/hour",
		"invite": "20/hour",
		# Nominatim policy is 1 req/sec absolute. We stay well under: a
		# user can pick a location ~once per minute realistically.
		"reverse_geocode": "60/hour",
		# Anonymous and legitimately bursty: one link pasted into a group
		# chat gets opened by everyone at once. Higher than `anon` on
		# purpose, and per-IP because there is no user to key on.
		"shared_list_public": "300/hour",
		# Ingesta de eventos: el cliente deduplica y manda en tandas de hasta
		# 50, así que un usuario muy activo hace unas pocas requests por
		# sesión. Holgado a propósito — perder eventos por throttle sesga el
		# número que se le muestra a un tercero, y no hay nada caro detrás
		# de este endpoint.
		"analytics": "600/hour",
		# Recuperación de contraseña. Cada pedido cuesta un email real, así
		# que el tope protege la casilla tanto como la cuenta. El canje es
		# más holgado porque tipear mal un código de 6 dígitos es normal;
		# quien acota la fuerza bruta ahí es el tope de 5 intentos por código.
		"password_reset": "5/hour",
		"password_reset_confirm": "10/hour",
		# Denuncias: holgado para que nadie se quede sin poder reportar, pero
		# con techo para que no se use como canal de spam contra el moderador.
		"report": "30/hour",
	},
	# Cuántos proxies hay entre el cliente y Django. VA ACÁ ADENTRO: DRF lee
	# sus settings del dict REST_FRAMEWORK, así que un NUM_PROXIES a nivel de
	# módulo queda en None y no hace nada (verificado: api_settings.NUM_PROXIES
	# seguía en None con el setting suelto puesto en 1).
	#
	# Sin esto, DRF no cae a REMOTE_ADDR mientras haya X-Forwarded-For: usa la
	# cadena XFF entera como identidad. Como nginx appendea con
	# $proxy_add_x_forwarded_for, esa cadena arranca con lo que mandó el
	# cliente, así que basta variar el header en cada request para tener un
	# cubo nuevo cada vez — el throttle deja de existir. Con 1, DRF toma la
	# última posición, la que puso nginx, y el prefijo falsificado no importa.
	# Afecta a login, register y shared_list_public, no sólo al reset.
	"NUM_PROXIES": int(os.environ.get("DJANGO_NUM_PROXIES", "1")),
}

# JWT
SIMPLE_JWT = {
	"ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
	"REFRESH_TOKEN_LIFETIME": timedelta(days=7),
	"ROTATE_REFRESH_TOKENS": True,
	# Firma cada token con el md5 del hash de la contraseña y lo compara en
	# cada request autenticado, usando el User que la autenticación ya trae de
	# la base — no agrega un query. Cambiar la contraseña invalida todo lo
	# emitido antes, que es lo que hace útil al reset (RF13) y de paso arregla
	# que cambiar la contraseña desde adentro no cerraba las otras sesiones.
	#
	# OJO AL DESPLEGAR: activarlo desloguea a TODOS una vez, porque los tokens
	# vigentes se firmaron sin el claim. Es intencional y se aceptó mientras el
	# padrón era chico; ver §4 "Compatibilidad" de docs/SPEC_RESET_PASSWORD.md.
	"CHECK_REVOKE_TOKEN": True,
}

# CORS
CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5174").split(",")

# CSRF
CSRF_TRUSTED_ORIGINS = os.environ.get("CSRF_TRUSTED_ORIGINS", "http://localhost:5174").split(",")

# Security — applied only in production (when DEBUG is off)
if not DEBUG:
	# Proxy headers (Traefik/nginx) — trust only behind a known reverse proxy
	SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
	# Off by default: our reverse proxy (Traefik via Coolify) already enforces
	# HTTPS and terminates TLS. Enabling this caused redirect loops in prod
	# because Traefik talks HTTP to the backend.
	SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SECURE_SSL_REDIRECT", "0") == "1"
	SESSION_COOKIE_SECURE = True
	CSRF_COOKIE_SECURE = True
	SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "31536000"))
	SECURE_HSTS_INCLUDE_SUBDOMAINS = True
	SECURE_HSTS_PRELOAD = True
	SECURE_CONTENT_TYPE_NOSNIFF = True
	SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
	X_FRAME_OPTIONS = "DENY"
