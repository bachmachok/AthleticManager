# training_manager/settings.py
from pathlib import Path
from datetime import timedelta
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# --- .env loader (без сторонніх пакетів) ---
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if not line or line.strip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)

# --- Базові налаштування ---
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-d*8-bovnb5a-bjew0jgf-b3(2gehllw_62&zz)*6(^=is0!gyp",
)
DEBUG = os.getenv("DEBUG", "True") == "True"
ALLOWED_HOSTS = (
    [h for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h] if not DEBUG else ["*"]
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "dashboard",

    # --- JWT: блэкліст refresh токенів (потребує міграцій) ---
    "rest_framework_simplejwt.token_blacklist",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # ВАЖЛИВО: LocaleMiddleware ПІСЛЯ Session і ПЕРЕД Common
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "training_manager.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "django.template.context_processors.static",
            ],
        },
    },
]

WSGI_APPLICATION = "training_manager.wsgi.application"

# --- База даних ---
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# --- Паролі ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Локаль/час ---
LANGUAGE_CODE = "uk"
TIME_ZONE = "Europe/Kyiv"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("en", "English"),
    ("uk", "Українська"),
]

# Шляхи, де лежать переклади (.po/.mo)
LOCALE_PATHS = [
    BASE_DIR / "locale",
    BASE_DIR / "training_manager" / "locale",  # гарантовано підхоплюємо ваші en/uk
]

# Cookie для мови (явно)
LANGUAGE_COOKIE_NAME = "django_language"
LANGUAGE_COOKIE_AGE = 60 * 60 * 24 * 365  # 1 рік
LANGUAGE_COOKIE_SAMESITE = os.getenv("LANGUAGE_COOKIE_SAMESITE", "Lax")
LANGUAGE_COOKIE_SECURE = not DEBUG
LANGUAGE_COOKIE_HTTPONLY = False  # дозволяє JS/шаблонам читати для UI-перемикачів
LANGUAGE_COOKIE_PATH = "/"

# --- Статика/медіа ---
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "dashboard" / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Логін/редіректи ---
LOGIN_URL = "/login/"
# Переконайся, що у urls є name="home" або зміни на потрібний
LOGIN_REDIRECT_URL = "home"

# --- Пошта ---
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False") == "True"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "webmaster@localhost")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# --- Кеш (для RSS та ін.) ---
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "athletic-manager-cache",
        "TIMEOUT": 60 * 60,  # дефолтний TTL 1 година
    }
}

# --- Джерела даних (RSS новини) ---
SPORT_NEWS_FEEDS = [
    u for u in (os.getenv("SPORT_NEWS_FEEDS", "")).split(",") if u.strip()
] or [
    "https://worldathletics.org/rss/news",
    "http://feeds.bbci.co.uk/sport/athletics/rss.xml",
]

# За бажанням — різні фіди для різних мов (views.index це підтримує)
SPORT_NEWS_FEEDS_MAP = {
    # "uk": [...],
    # "en": [...],
}

# --- Безпека / проксі ---
CSRF_TRUSTED_ORIGINS = [o for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https") if os.getenv("ENABLE_PROXY_SSL", "False") == "True" else None
)

# --- JWT (SimpleJWT) ---
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "30"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    # SIGNING_KEY за замовчуванням SECRET_KEY; ALGORITHM = 'HS256'
}

# --- Cookie-політики ---
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")

# --- Додаткова продакшн-безпека (керується .env) ---
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False") == "True"
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "False") == "True"
SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "False") == "True"

# --- Логи ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO" if DEBUG else "WARNING"},
}
