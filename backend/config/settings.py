from pathlib import Path

import environ


BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, "django-insecure-change-me"),
    ALLOWED_HOSTS=(list, ["127.0.0.1", "localhost"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:5173"]),
    DB_NAME=(str, "ns_auto_testing"),
    DB_USER=(str, "ns_auto_testing"),
    DB_PASSWORD=(str, ""),
    DB_HOST=(str, "127.0.0.1"),
    DB_PORT=(int, 5432),
    REDIS_URL=(str, "redis://127.0.0.1:6379/1"),
    DJANGO_CACHE_URL=(str, "redis://127.0.0.1:6379/2"),
    CELERY_RESULT_EXPIRES=(int, 24 * 60 * 60),
    JAVA_BIN=(str, "java"),
    JMETER_BIN=(str, "jmeter"),
    PERF_RESULT_DIR=(str, str(BASE_DIR / "perf_results")),
    PERF_USE_CELERY=(bool, False),
    AUTH_COOKIE_SECURE=(bool, None),
    API_DEBUG_ALLOW_PRIVATE_NETWORK=(bool, False),
    API_DEBUG_MAX_TIMEOUT_SECONDS=(int, 30),
    API_DEBUG_MAX_RESPONSE_BYTES=(int, 1024 * 1024),
    ACCESS_TOKEN_SECONDS=(int, 24 * 60 * 60),
    REFRESH_TOKEN_SECONDS=(int, 15 * 24 * 60 * 60),
    REMEMBER_ME_REFRESH_TOKEN_SECONDS=(int, 30 * 24 * 60 * 60),
    USER_SESSION_SECONDS=(int, 24 * 60 * 60),
    REMEMBER_ME_USER_SESSION_SECONDS=(int, 30 * 24 * 60 * 60),
    FRONTEND_BASE_URL=(str, "http://localhost:5173"),
)
env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "django_filters",
    "django_celery_beat",
    "apps.core",
    "apps.accounts",
    "apps.projects",
    "apps.api_testing",
    "apps.ui_testing",
    "apps.test_runs",
    "apps.scheduling",
    "apps.performance_testing",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
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
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST"),
        "PORT": env("DB_PORT"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
FRONTEND_DIST_DIR = BASE_DIR.parent / "frontend" / "dist"
FRONTEND_BASE_URL = env("FRONTEND_BASE_URL").rstrip("/")
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env("CORS_ALLOWED_ORIGINS")

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["apps.core.renderers.UnifiedJSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "apps.accounts.authentication.StrongTokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "apps.core.exceptions.unified_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user": "1200/hour",
        "anon": "60/hour",
        "api_debug": "120/hour",
        "login": "20/minute",
    },
}

CELERY_BROKER_URL = env("REDIS_URL")
CELERY_RESULT_BACKEND = env("REDIS_URL")
CELERY_RESULT_EXPIRES = env("CELERY_RESULT_EXPIRES")
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_BEAT_SCHEDULE = {
    "dispatch-scheduled-plans-every-minute": {
        "task": "apps.scheduling.tasks.dispatch_scheduled_plans",
        "schedule": 60.0,
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("DJANGO_CACHE_URL"),
    }
}

API_DEBUG_ALLOW_PRIVATE_NETWORK = env("API_DEBUG_ALLOW_PRIVATE_NETWORK")
API_DEBUG_MAX_TIMEOUT_SECONDS = env("API_DEBUG_MAX_TIMEOUT_SECONDS")
API_DEBUG_MAX_RESPONSE_BYTES = env("API_DEBUG_MAX_RESPONSE_BYTES")
ACCESS_TOKEN_SECONDS = env("ACCESS_TOKEN_SECONDS")
REFRESH_TOKEN_SECONDS = env("REFRESH_TOKEN_SECONDS")
REMEMBER_ME_REFRESH_TOKEN_SECONDS = env("REMEMBER_ME_REFRESH_TOKEN_SECONDS")
USER_SESSION_SECONDS = env("USER_SESSION_SECONDS")
REMEMBER_ME_USER_SESSION_SECONDS = env("REMEMBER_ME_USER_SESSION_SECONDS")
JAVA_BIN = env("JAVA_BIN")
JMETER_BIN = env("JMETER_BIN")
PERF_RESULT_DIR = env("PERF_RESULT_DIR")
PERF_USE_CELERY = env("PERF_USE_CELERY")
AUTH_COOKIE_SECURE = env("AUTH_COOKIE_SECURE")
