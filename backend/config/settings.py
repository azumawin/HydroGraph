"""Django settings for the HydroGraph backend."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Local secrets live in backend/.env (gitignored); real environment variables win.
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _key, _sep, _value = _line.partition("=")
        if _sep and not _line.lstrip().startswith("#"):
            _ = os.environ.setdefault(_key.strip(), _value.strip())


SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-q7(k7=(7_wqr9s0dn4l@!&tvj*1)c48_ypt4a6s-f_kmm30rk0",
)
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")


INSTALLED_APPS = [
    # first, so `runserver` serves ASGI and can hold SSE streams open
    "daphne",
    "corsheaders",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DJANGO_DB_PATH", BASE_DIR / "db.sqlite3"),
        # WAL: the stream's reads never wait on the simulator's writes.
        # NORMAL: no disk flush per insert (safe with WAL; a crash loses at most
        # the last few readings).
        "OPTIONS": {
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;"
        },
    }
}


LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# runserver logs every request; with the simulator posting several per second that
# buries everything else, so only 4xx/5xx responses are logged.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {"django.channels.server": {"level": "WARNING"}},
}

# The frontend dev server is another origin, and proxying it buffers the stream,
# so the API answers any origin. There is no auth to protect.
CORS_ALLOW_ALL_ORIGINS = True
CORS_URLS_REGEX = r"^/api/.*$"

# The health assistant's LLM, on Ollama Cloud. Without a key the chat answers 503.
OLLAMA_URL = os.environ.get("OLLAMA_URL", "https://ollama.com/api/chat")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gpt-oss:120b")
OLLAMA_TIMEOUT_S = float(os.environ.get("OLLAMA_TIMEOUT_S", "60"))

# Per client IP, for the health assistant only (api/assistant.py).
ASSISTANT_RATE = os.environ.get("ASSISTANT_RATE", "10/min")
ASSISTANT_DAILY_RATE = os.environ.get("ASSISTANT_DAILY_RATE", "200/day")
