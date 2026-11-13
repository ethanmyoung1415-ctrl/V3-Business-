"""Preproduction Django portal. Default is fail-closed; NOT ready to host publicly."""
import os
from pathlib import Path
BASE_DIR=Path(__file__).resolve().parent.parent
LOCAL_DEV=os.environ.get("V3_LOCAL_DEV")=="1"
# Deliberate product-level release gate. Production hosting is not approved.
if not LOCAL_DEV:
    raise RuntimeError("V3 portal public deployment is disabled pending security review and owner authorization")
DEBUG=LOCAL_DEV
SECRET_KEY=os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if LOCAL_DEV:
        SECRET_KEY="INSECURE-LOCAL-TESTS-ONLY-do-not-deploy"
    else:
        raise RuntimeError("DJANGO_SECRET_KEY required when V3_LOCAL_DEV is disabled")
ALLOWED_HOSTS=["127.0.0.1","localhost","testserver"] if LOCAL_DEV else [
    x.strip() for x in os.environ.get("DJANGO_ALLOWED_HOSTS","").split(",") if x.strip()]
if not ALLOWED_HOSTS:raise RuntimeError("DJANGO_ALLOWED_HOSTS required")
INSTALLED_APPS=[
    "django.contrib.admin","django.contrib.auth","django.contrib.contenttypes",
    "django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles",
    "catalog_portal",
]
MIDDLEWARE=[
    "django.middleware.security.SecurityMiddleware",
    "v3portal.local_only.LocalOnlyPortal",
    "v3portal.emergency_middleware.EmergencyStopMiddleware",
    "v3portal.login_throttle.LocalLoginThrottle",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "v3portal.security_headers.PrivatePortalHeaders",
]
ROOT_URLCONF="v3portal.urls"
TEMPLATES=[{"BACKEND":"django.template.backends.django.DjangoTemplates",
            "DIRS":[BASE_DIR/"templates"],"APP_DIRS":True,
            "OPTIONS":{"context_processors":[
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION="v3portal.wsgi.application"
# PostgreSQL compatibility is test-only. It never relaxes the localhost gate.
POSTGRES_TEST_MODE=os.environ.get("V3_TEST_POSTGRES")=="1"
if POSTGRES_TEST_MODE:
    required={
        "NAME":os.environ.get("V3_TEST_PG_DATABASE",""),
        "USER":os.environ.get("V3_TEST_PG_USER",""),
        "PASSWORD":os.environ.get("V3_TEST_PG_PASSWORD",""),
        "HOST":os.environ.get("V3_TEST_PG_HOST","127.0.0.1"),
        "PORT":os.environ.get("V3_TEST_PG_PORT","5432"),
    }
    if not all(required.values()):
        raise RuntimeError("ephemeral PostgreSQL test settings are incomplete")
    DATABASES={"default":{"ENGINE":"django.db.backends.postgresql",
                         **required,"CONN_MAX_AGE":0,
                         "OPTIONS":{"connect_timeout":5}}}
else:
    DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3",
                          "NAME":BASE_DIR/".local-v3portal.sqlite3"}}
AUTH_PASSWORD_VALIDATORS=[
    {"NAME":"django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME":"django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS":{"min_length":12}},
    {"NAME":"django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME":"django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE="en-us"
TIME_ZONE="UTC"
USE_I18N=True
USE_TZ=True
STATIC_URL="static/"
MEDIA_ROOT=BASE_DIR/".local_uploads"
MEDIA_URL="/private-not-served/"
DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
LOGIN_URL="/login/"
LOGIN_REDIRECT_URL="/"
LOGOUT_REDIRECT_URL="/login/"
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE="Strict"
CSRF_COOKIE_SAMESITE="Strict"
SESSION_COOKIE_SECURE=not LOCAL_DEV
CSRF_COOKIE_SECURE=not LOCAL_DEV
SECURE_SSL_REDIRECT=not LOCAL_DEV
SECURE_HSTS_SECONDS=0 if LOCAL_DEV else 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=not LOCAL_DEV
SECURE_CONTENT_TYPE_NOSNIFF=True
X_FRAME_OPTIONS="DENY"
DATA_UPLOAD_MAX_MEMORY_SIZE=16_000_000
FILE_UPLOAD_MAX_MEMORY_SIZE=1_000_000
FILE_UPLOAD_PERMISSIONS=0o600
