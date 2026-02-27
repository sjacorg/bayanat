# -*- coding: utf-8 -*-
import os
from datetime import timedelta

import bleach
import redis
from dotenv import load_dotenv, find_dotenv
from flask import current_app, has_app_context

from enferno.utils.config_utils import ConfigManager
from enferno.utils.dep_utils import dep_utils
from enferno.admin.constants import Constants
from enferno.utils.notification_config import NOTIFICATIONS_DEFAULT_CONFIG

NotificationEvent = Constants.NotificationEvent

load_dotenv(find_dotenv())
manager = ConfigManager()


def uia_username_mapper(identity):
    # we allow pretty much anything - but we bleach it.
    return bleach.clean(identity, strip=True)


class Config(object):
    """Base configuration."""

    BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000/")

    SECRET_KEY = os.environ.get("SECRET_KEY")
    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    DEBUG_TB_ENABLED = os.environ.get("DEBUG_TB_ENABLED", 0)
    DEBUG_TB_INTERCEPT_REDIRECTS = False

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI")
    # Databaset
    # SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    POSTGRES_USER = os.environ.get("POSTGRES_USER", "")
    POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")
    POSTGRES_DB = os.environ.get("POSTGRES_DB", "bayanat")
    POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")

    if (POSTGRES_USER and POSTGRES_PASSWORD) or POSTGRES_HOST != "localhost":
        SQLALCHEMY_DATABASE_URI = (
            f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}"
        )
    else:
        SQLALCHEMY_DATABASE_URI = f"postgresql:///{POSTGRES_DB}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
    REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0"

    # Celery
    # Has to be in small case
    celery_broker_url = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/2"
    result_backend = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/3"

    # Security
    SECURITY_REGISTERABLE = manager.get_config("SECURITY_REGISTERABLE")
    SECURITY_RECOVERABLE = manager.get_config("SECURITY_RECOVERABLE")
    SECURITY_CONFIRMABLE = manager.get_config("SECURITY_CONFIRMABLE")
    SECURITY_CHANGEABLE = True
    SECURITY_SEND_PASSWORD_CHANGE_EMAIL = False
    SECURITY_TRACKABLE = True
    SECURITY_PASSWORD_HASH = "argon2"
    SECURITY_PASSWORD_SALT = os.environ.get("SECURITY_PASSWORD_SALT")
    SECURITY_POST_LOGIN_VIEW = "/dashboard/"
    SECURITY_POST_CONFIRM_VIEW = "/dashboard/"

    SECURITY_USER_IDENTITY_ATTRIBUTES = [
        {"username": {"mapper": uia_username_mapper, "case_insensitive": True}}
    ]
    SECURITY_USERNAME_ENABLE = True

    SECURITY_MULTI_FACTOR_RECOVERY_CODES = True
    SECURITY_MULTI_FACTOR_RECOVERY_CODES_N = 3
    SECURITY_MULTI_FACTOR_RECOVERY_CODES_KEYS = None
    SECURITY_MULTI_FACTOR_RECOVERY_CODE_TTL = None

    # Disable token apis

    SECURITY_TWO_FACTOR_ENABLED_METHODS = [
        "authenticator"
    ]  # 'sms' also valid but requires an sms provider
    SECURITY_TWO_FACTOR = os.environ.get("SECURITY_TWO_FACTOR", True)
    SECURITY_TWO_FACTOR_RESCUE_MAIL = os.environ.get("SECURITY_TWO_FACTOR_RESCUE_MAIL")

    # Enable only session auth
    SECURITY_API_ENABLED_METHODS = ["session"]
    security_freshness = manager.get_config("SECURITY_FRESHNESS")
    SECURITY_FRESHNESS = timedelta(minutes=security_freshness)

    security_freshness_grace_period = manager.get_config("SECURITY_FRESHNESS_GRACE_PERIOD")
    SECURITY_FRESHNESS_GRACE_PERIOD = timedelta(minutes=security_freshness_grace_period)

    SECURITY_TWO_FACTOR_REQUIRED = manager.get_config("SECURITY_TWO_FACTOR_REQUIRED")

    SECURITY_PASSWORD_LENGTH_MIN = manager.get_config("SECURITY_PASSWORD_LENGTH_MIN")

    SECURITY_PASSWORD_COMPLEXITY_CHECKER = "zxcvbn"

    SECURITY_ZXCVBN_MINIMUM_SCORE = manager.get_config("SECURITY_ZXCVBN_MINIMUM_SCORE")

    # Strong session protection
    SESSION_PROTECTION = "strong"

    # 2fa
    SECURITY_TOTP_SECRETS = {"1": os.environ.get("SECURITY_TOTP_SECRETS")}
    SECURITY_TOTP_ISSUER = "Bayanat"

    SECURITY_WEBAUTHN = True
    SECURITY_WAN_ALLOW_AS_FIRST_FACTOR = False
    SECURITY_WAN_ALLOW_AS_MULTI_FACTOR = True
    SECURITY_WAN_ALLOW_AS_VERIFY = ["first", "secondary"]
    SECURITY_WAN_ALLOW_USER_HINTS = True

    DISABLE_MULTIPLE_SESSIONS = manager.get_config("DISABLE_MULTIPLE_SESSIONS")
    SESSION_RETENTION_PERIOD = manager.get_config("SESSION_RETENTION_PERIOD")

    # Recaptcha
    RECAPTCHA_ENABLED = manager.get_config("RECAPTCHA_ENABLED")
    RECAPTCHA_PUBLIC_KEY = manager.get_config("RECAPTCHA_PUBLIC_KEY")
    RECAPTCHA_PRIVATE_KEY = manager.get_config("RECAPTCHA_PRIVATE_KEY")

    # Session
    SESSION_TYPE = "redis"
    SESSION_REDIS = redis.from_url(f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/1")
    PERMANENT_SESSION_LIFETIME = 3600

    # Google 0Auth
    GOOGLE_OAUTH_ENABLED = manager.get_config("GOOGLE_OAUTH_ENABLED")
    GOOGLE_CLIENT_ID = manager.get_config("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = manager.get_config("GOOGLE_CLIENT_SECRET")
    GOOGLE_DISCOVERY_URL = manager.get_config("GOOGLE_DISCOVERY_URL")

    GOOGLE_CLIENT_ALLOWED_DOMAIN = os.environ.get("GOOGLE_CLIENT_ALLOWED_DOMAIN", False)

    # File Upload Settings: switch to True to store files privately within the enferno/media directory
    FILESYSTEM_LOCAL = manager.get_config("FILESYSTEM_LOCAL")

    # Access Control settings
    ACCESS_CONTROL_RESTRICTIVE = manager.get_config("ACCESS_CONTROL_RESTRICTIVE")
    AC_USERS_CAN_RESTRICT_NEW = manager.get_config("AC_USERS_CAN_RESTRICT_NEW")

    # Activities
    ACTIVITIES = manager.get_config("ACTIVITIES")
    ACTIVITIES_LIST = [x for x, value in ACTIVITIES.items() if value]
    # minimum retention for 90 days
    activities_retention = max(90, int(manager.get_config("ACTIVITIES_RETENTION")))
    ACTIVITIES_RETENTION = timedelta(days=activities_retention)

    # Allowed file upload extensions
    MEDIA_ALLOWED_EXTENSIONS = manager.get_config("MEDIA_ALLOWED_EXTENSIONS")
    MEDIA_UPLOAD_MAX_FILE_SIZE = manager.get_config("MEDIA_UPLOAD_MAX_FILE_SIZE")
    SHEETS_ALLOWED_EXTENSIONS = manager.get_config("SHEETS_ALLOWED_EXTENSIONS")

    # Enable data import tool
    ETL_TOOL = manager.get_config("ETL_TOOL")
    ETL_PATH_IMPORT = manager.get_config("ETL_PATH_IMPORT")
    ETL_ALLOWED_PATH = os.environ.get("ETL_ALLOWED_PATH", None)

    EXPORT_TOOL = manager.get_config("EXPORT_TOOL")
    # Export file expiry in hours
    export_default_expiry = manager.get_config("EXPORT_DEFAULT_EXPIRY")
    EXPORT_DEFAULT_EXPIRY = timedelta(hours=export_default_expiry)

    # Enable data deduplication tool
    DEDUP_TOOL = manager.get_config("DEDUP_TOOL")

    # Valid video extension list (will be processed during ETL)
    ETL_VID_EXT = manager.get_config("ETL_VID_EXT")

    OCR_ENABLED = manager.get_config("OCR_ENABLED")
    OCR_EXT = manager.get_config("OCR_EXT")
    TESSERACT_CMD = os.environ.get("TESSERACT_CMD", "/usr/bin/tesseract")
    GOOGLE_VISION_API_KEY = os.environ.get("GOOGLE_VISION_API_KEY") or manager.get_config(
        "GOOGLE_VISION_API_KEY"
    )
    OCR_PROVIDER = os.environ.get("OCR_PROVIDER") or manager.get_config("OCR_PROVIDER")
    LLM_OCR_URL = os.environ.get("LLM_OCR_URL") or manager.get_config("LLM_OCR_URL")
    LLM_OCR_MODEL = os.environ.get("LLM_OCR_MODEL") or manager.get_config("LLM_OCR_MODEL")
    LLM_OCR_API_KEY = os.environ.get("LLM_OCR_API_KEY") or manager.get_config("LLM_OCR_API_KEY")

    # S3 settings
    # Bucket needs to be private with public access blocked
    AWS_ACCESS_KEY_ID = manager.get_config("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = manager.get_config("AWS_SECRET_ACCESS_KEY")
    S3_BUCKET = manager.get_config("S3_BUCKET")
    AWS_REGION = manager.get_config("AWS_REGION")

    # i18n
    LANGUAGES = {
        "ar": "العربية",
        "en": "English",
        "es": "español",
        "fa": "فارسی",
        "fr": "français",
        "ru": "русский",
        "uk": "українська",
        "zh_Hans": "简体中文",
        "zh_Hant": "繁體中文",
    }

    BABEL_DEFAULT_LOCALE = manager.get_config("BABEL_DEFAULT_LOCALE")
    # extract messages with the following command
    # pybabel extract -F babel.cfg -k _l -o messages.pot .
    # generate a new language using the following command
    # pybabel init -i messages.pot -d enferno/translations -l ar
    # to update existing translations
    # pybabel update -i messages.pot -d enferno/translations
    # compile translation using the following
    # pybabel compile -d enferno/translations

    MAPS_API_ENDPOINT = manager.get_config("MAPS_API_ENDPOINT")
    GOOGLE_MAPS_API_KEY = manager.get_config("GOOGLE_MAPS_API_KEY")

    # Deduplication

    # specify min and max distance for matching
    DEDUP_LOW_DISTANCE = manager.get_config("DEDUP_LOW_DISTANCE")
    DEDUP_MAX_DISTANCE = manager.get_config("DEDUP_MAX_DISTANCE")

    # how many items to process every cycle (cycles are processed based on the time interval below)
    DEDUP_BATCH_SIZE = manager.get_config("DEDUP_BATCH_SIZE")

    # the time in seconds at which a batch of deduplication items is processed
    DEDUP_INTERVAL = manager.get_config("DEDUP_INTERVAL")

    # Sheet import tool settings
    SHEET_IMPORT = manager.get_config("SHEET_IMPORT")
    IMPORT_DIR = "enferno/imports"

    geo_map_default_center = manager.get_config("GEO_MAP_DEFAULT_CENTER")

    if geo_map_default_center:
        GEO_MAP_DEFAULT_CENTER_LAT = geo_map_default_center.get("lat")
        GEO_MAP_DEFAULT_CENTER_LNG = geo_map_default_center.get("lng")
        GEO_MAP_DEFAULT_CENTER_RADIUS = geo_map_default_center.get("radius", 1000)

    ITEMS_PER_PAGE_OPTIONS = manager.get_config("ITEMS_PER_PAGE_OPTIONS")
    VIDEO_RATES = manager.get_config("VIDEO_RATES")
    # secure cookies (flask core)
    SESSION_COOKIE_SECURE = os.environ.get("SECURE_COOKIES", "True") == "True"
    REMEMBER_COOKIE_SECURE = os.environ.get("SECURE_COOKIES", "True") == "True"
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # flask-security cookie
    SECURITY_CSRF_COOKIE = {
        # Overrides default secure = False to require HTTPS.
        "samesite": "Strict",
        "httponly": False,
        "secure": os.environ.get("SECURE_COOKIES", "True") == "True",
    }
    # Content Security Policy
    # Disabled by default until nonces are added to inline scripts in templates
    CSP_ENABLED = os.environ.get("CSP_ENABLED", "False").lower() == "true"
    # Report-only mode requires CSP_REPORT_URI to be set
    CSP_REPORT_ONLY = os.environ.get("CSP_REPORT_ONLY", "False").lower() == "true"
    CSP_REPORT_URI = os.environ.get("CSP_REPORT_URI", None)
    FORCE_HTTPS = os.environ.get("FORCE_HTTPS", "False").lower() == "true"

    # logging
    APP_LOG_ENABLED = os.environ.get("APP_LOG_ENABLED", "True").lower() == "true"
    CELERY_LOG_ENABLED = os.environ.get("CELERY_LOG_ENABLED", "True").lower() == "true"
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_DIR = os.environ.get("LOG_DIR", "logs")
    LOG_FILE = os.environ.get("LOG_FILE", "bayanat.log")
    LOG_BACKUP_COUNT = os.environ.get("LOG_BACKUP_COUNT", 5)

    # backups
    BACKUPS = os.environ.get("BACKUPS", False)
    BACKUP_INTERVAL = int(os.environ.get("BACKUP_INTERVAL", 1))
    BACKUPS_LOCAL_PATH = os.environ.get("BACKUPS_LOCAL_PATH", "backups/")
    BACKUPS_S3_BUCKET = os.environ.get("BACKUPS_S3_BUCKET")
    BACKUPS_AWS_ACCESS_KEY_ID = os.environ.get("BACKUPS_AWS_ACCESS_KEY_ID")
    BACKUPS_AWS_SECRET_ACCESS_KEY = os.environ.get("BACKUPS_AWS_SECRET_ACCESS_KEY")
    BACKUPS_AWS_REGION = os.environ.get("BACKUPS_AWS_REGION")

    # Setup Wizard
    SETUP_COMPLETE = manager.get_config("SETUP_COMPLETE")

    ADV_ANALYSIS = manager.get_config("ADV_ANALYSIS")

    # Location Admin Levels
    LOCATIONS_INCLUDE_POSTAL_CODE = manager.get_config("LOCATIONS_INCLUDE_POSTAL_CODE")

    # Email Settings
    MAIL_ENABLED = manager.get_config("MAIL_ENABLED")
    MAIL_ALLOWED_DOMAINS = manager.get_config("MAIL_ALLOWED_DOMAINS")
    MAIL_SERVER = manager.get_config("MAIL_SERVER")
    MAIL_PORT = int(manager.get_config("MAIL_PORT"))
    MAIL_USE_TLS = manager.get_config("MAIL_USE_TLS")
    MAIL_USE_SSL = manager.get_config("MAIL_USE_SSL")
    MAIL_USERNAME = manager.get_config("MAIL_USERNAME")
    MAIL_PASSWORD = manager.get_config("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = manager.get_config("MAIL_DEFAULT_SENDER")

    TRANSCRIPTION_ENABLED = manager.get_config("TRANSCRIPTION_ENABLED")
    WEB_IMPORT = manager.get_config("WEB_IMPORT")
    WHISPER_MODEL = manager.get_config("WHISPER_MODEL")
    # YTDLP Proxy Settings
    YTDLP_PROXY = manager.get_config("YTDLP_PROXY")
    YTDLP_ALLOWED_DOMAINS = manager.get_config("YTDLP_ALLOWED_DOMAINS")
    YTDLP_COOKIES = manager.get_config("YTDLP_COOKIES")

    NOTIFICATIONS = manager.get_config("NOTIFICATIONS")
    # Dependency Flags
    HAS_WHISPER = dep_utils.has_whisper
    HAS_TESSERACT = dep_utils.has_tesseract

    @classmethod
    def get(cls, key, default=None):
        """
        Smart config getter that automatically uses Flask app context when available.

        In Flask app context (requests/tests): uses current_app.config
        Outside app context (CLI/standalone): uses Config class attributes

        Args:
            key: Configuration key name
            default: Default value if not found

        Returns:
            Configuration value
        """
        if has_app_context():
            return current_app.config.get(key, default)
        else:
            return getattr(cls, key, default)


class TestConfig:
    """Completely isolated test configuration - no external dependencies."""

    TESTING = True

    # Flask Core Settings
    SECRET_KEY = "test-secret-key-not-for-production"
    BASE_URL = "http://127.0.0.1:5000/"
    APP_DIR = os.path.abspath(os.path.dirname(__file__))
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    DEBUG_TB_ENABLED = 0
    DEBUG_TB_INTERCEPT_REDIRECTS = False

    # Database - use Docker config if available, otherwise local
    POSTGRES_USER = os.environ.get("POSTGRES_USER", "")
    POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")
    POSTGRES_DB = "bayanat_test"
    POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")

    if (POSTGRES_USER and POSTGRES_PASSWORD) or POSTGRES_HOST != "localhost":
        SQLALCHEMY_DATABASE_URI = (
            f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}"
        )
    else:
        SQLALCHEMY_DATABASE_URI = "postgresql:///bayanat_test"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis - use Docker Redis for main Redis, fakeredis only for sessions
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
    REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0"

    # Celery - use in-memory for tests to avoid Redis dependency
    celery_broker_url = "memory://"
    result_backend = "cache+memory://"

    # Session Redis - always use fakeredis for tests
    SESSION_TYPE = "redis"
    import fakeredis

    SESSION_REDIS = fakeredis.FakeRedis()
    PERMANENT_SESSION_LIFETIME = 3600

    # Security Settings
    SECURITY_REGISTERABLE = False
    SECURITY_RECOVERABLE = False
    SECURITY_CONFIRMABLE = False
    SECURITY_CHANGEABLE = True
    SECURITY_SEND_PASSWORD_CHANGE_EMAIL = False
    SECURITY_TRACKABLE = True
    SECURITY_PASSWORD_HASH = "argon2"
    SECURITY_PASSWORD_SALT = os.environ.get("SECURITY_PASSWORD_SALT", "test-salt")
    SECURITY_POST_LOGIN_VIEW = "/dashboard/"
    SECURITY_POST_CONFIRM_VIEW = "/dashboard/"
    SECURITY_USER_IDENTITY_ATTRIBUTES = [
        {"username": {"mapper": uia_username_mapper, "case_insensitive": True}}
    ]
    SECURITY_USERNAME_ENABLE = True
    SECURITY_MULTI_FACTOR_RECOVERY_CODES = True
    SECURITY_MULTI_FACTOR_RECOVERY_CODES_N = 3
    SECURITY_MULTI_FACTOR_RECOVERY_CODES_KEYS = None
    SECURITY_MULTI_FACTOR_RECOVERY_CODE_TTL = None
    SECURITY_TWO_FACTOR_ENABLED_METHODS = ["authenticator"]
    SECURITY_TWO_FACTOR = True
    SECURITY_TWO_FACTOR_RESCUE_MAIL = "test@example.com"
    SECURITY_API_ENABLED_METHODS = ["session"]
    SECURITY_FRESHNESS = timedelta(minutes=30)
    SECURITY_FRESHNESS_GRACE_PERIOD = timedelta(minutes=30)
    SECURITY_TWO_FACTOR_REQUIRED = False
    SECURITY_PASSWORD_LENGTH_MIN = 8  # Minimum required by validation
    SECURITY_PASSWORD_COMPLEXITY_CHECKER = "zxcvbn"
    SECURITY_ZXCVBN_MINIMUM_SCORE = 3  # Required for password validation tests
    SESSION_PROTECTION = "strong"
    SECURITY_TOTP_SECRETS = {"1": "test-totp-secret"}
    SECURITY_TOTP_ISSUER = "Bayanat"
    SECURITY_WEBAUTHN = True
    SECURITY_WAN_ALLOW_AS_FIRST_FACTOR = False
    SECURITY_WAN_ALLOW_AS_MULTI_FACTOR = True
    SECURITY_WAN_ALLOW_AS_VERIFY = ["first", "secondary"]
    SECURITY_WAN_ALLOW_USER_HINTS = True

    # Session & User Settings
    DISABLE_MULTIPLE_SESSIONS = True
    SESSION_RETENTION_PERIOD = 30

    # Access Control & Security
    ACCESS_CONTROL_RESTRICTIVE = False
    AC_USERS_CAN_RESTRICT_NEW = False
    RECAPTCHA_ENABLED = False
    RECAPTCHA_PUBLIC_KEY = "dummy_recaptcha_public_key"
    RECAPTCHA_PRIVATE_KEY = "dummy_recaptcha_private_key"

    # OAuth & External Auth
    GOOGLE_OAUTH_ENABLED = False
    GOOGLE_CLIENT_ID = "dummy_client_id"
    GOOGLE_CLIENT_SECRET = "dummy_client_secret"
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
    GOOGLE_CLIENT_ALLOWED_DOMAIN = False

    # Activities & Logging
    ACTIVITIES = {
        "APPROVE": True,
        "BULK": True,
        "CREATE": True,
        "DELETE": True,
        "DOWNLOAD": True,
        "LOGIN": True,
        "LOGOUT": True,
        "REJECT": True,
        "REQUEST": True,
        "REVIEW": True,
        "SEARCH": True,
        "SELF-ASSIGN": True,
        "UPDATE": True,
        "UPLOAD": True,
        "VIEW": True,
    }
    ACTIVITIES_RETENTION = timedelta(days=90)
    ACTIVITIES_LIST = [x for x, value in ACTIVITIES.items() if value]

    # File Storage & AWS
    FILESYSTEM_LOCAL = 1
    AWS_ACCESS_KEY_ID = "dummy_access_key"
    AWS_SECRET_ACCESS_KEY = "dummy_secret_key"
    S3_BUCKET = "dummy_bucket"
    AWS_REGION = "dummy_region"

    # Media & File Upload
    MEDIA_ALLOWED_EXTENSIONS = ["mp4", "webm", "jpg", "gif", "png", "pdf", "doc", "txt"]
    MEDIA_UPLOAD_MAX_FILE_SIZE = 1000
    SHEETS_ALLOWED_EXTENSIONS = ["csv", "xls", "xlsx"]

    # Data Tools
    ETL_TOOL = True
    ETL_PATH_IMPORT = True
    ETL_ALLOWED_PATH = None
    EXPORT_TOOL = False
    EXPORT_DEFAULT_EXPIRY = timedelta(hours=2)
    DEDUP_TOOL = False
    DEDUP_LOW_DISTANCE = 0.3
    DEDUP_MAX_DISTANCE = 0.5
    DEDUP_BATCH_SIZE = 30
    DEDUP_INTERVAL = 3
    SHEET_IMPORT = True
    ETL_VID_EXT = [
        "webm",
        "mkv",
        "flv",
        "vob",
        "ogv",
        "ogg",
        "rrc",
        "gifv",
        "mng",
        "mov",
        "avi",
        "qt",
        "wmv",
        "yuv",
        "rm",
        "asf",
        "amv",
        "mp4",
        "m4p",
        "m4v",
        "mpg",
        "mp2",
        "mpeg",
        "mpe",
        "mpv",
        "svi",
        "3gp",
        "3g2",
        "mxf",
        "roq",
        "nsv",
        "flv",
        "f4v",
        "f4p",
        "f4a",
        "f4b",
        "mts",
        "lvr",
        "m2ts",
        "png",
        "jpeg",
        "jpg",
        "gif",
        "webp",
        "pdf",
    ]

    # OCR Settings
    OCR_ENABLED = False
    OCR_EXT = ["png", "jpeg", "tiff", "jpg", "gif", "webp", "bmp", "pnm", "pdf"]
    TESSERACT_CMD = "/usr/bin/tesseract"
    GOOGLE_VISION_API_KEY = "dummy_vision_api_key_for_testing"
    OCR_PROVIDER = "google_vision"
    LLM_OCR_URL = "http://localhost:11434"
    LLM_OCR_MODEL = "llava"
    LLM_OCR_API_KEY = ""

    # Geo & Maps
    GEO_MAP_DEFAULT_CENTER_LAT = 33.510414
    GEO_MAP_DEFAULT_CENTER_LNG = 36.278336
    GEO_MAP_DEFAULT_CENTER_RADIUS = 1000
    GEO_MAP_DEFAULT_CENTER = {"lat": 33.510414, "lng": 36.278336, "radius": 1000}
    MAPS_API_ENDPOINT = "https://{s}.tile.osm.org/{z}/{x}/{y}.png"
    GOOGLE_MAPS_API_KEY = "dummy_maps_api_key_for_testing"

    # UI Settings
    ITEMS_PER_PAGE_OPTIONS = [10, 30, 100]
    VIDEO_RATES = [0.25, 0.5, 1, 1.5, 2, 4]

    # Internationalization
    LANGUAGES = {
        "ar": "العربية",
        "en": "English",
        "es": "español",
        "fa": "فارسی",
        "fr": "français",
        "ru": "русский",
        "uk": "українська",
        "zh_Hans": "简体中文",
        "zh_Hant": "繁體中文",
    }
    BABEL_DEFAULT_LOCALE = "en"

    # Location Settings
    LOCATIONS_INCLUDE_POSTAL_CODE = False

    # Email Settings
    MAIL_ENABLED = False
    MAIL_ALLOWED_DOMAINS = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]
    MAIL_SERVER = "dummy-smtp-server"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = "dummy-username"
    MAIL_PASSWORD = "dummy-password"
    MAIL_DEFAULT_SENDER = "dummy-sender@example.com"

    # AI/ML Features
    TRANSCRIPTION_ENABLED = False
    WEB_IMPORT = False
    WHISPER_MODEL = "base"
    ADV_ANALYSIS = False

    # YTDLP Settings
    YTDLP_PROXY = ""
    YTDLP_ALLOWED_DOMAINS = ["youtube.com", "facebook.com", "instagram.com", "twitter.com"]
    YTDLP_COOKIES = ""

    # Notifications
    NOTIFICATIONS = NOTIFICATIONS_DEFAULT_CONFIG

    # Dependencies (from dep_utils)
    HAS_WHISPER = dep_utils.has_whisper  # Use actual dependency detection
    HAS_TESSERACT = dep_utils.has_tesseract  # Use actual dependency detection

    # Setup & System
    SETUP_COMPLETE = True  # Mark as complete to bypass setup wizard in tests
    IMPORT_DIR = "tests/imports"

    # Cookies & Security
    SESSION_COOKIE_SECURE = False  # Disabled for test HTTP
    REMEMBER_COOKIE_SECURE = False  # Disabled for test HTTP
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SECURITY_CSRF_COOKIE = {
        "samesite": "Strict",
        "httponly": False,
        "secure": False,  # Disabled for test HTTP
    }

    # Content Security Policy (disabled for tests)
    CSP_ENABLED = False
    CSP_REPORT_ONLY = True
    CSP_REPORT_URI = None
    FORCE_HTTPS = False

    # Logging
    APP_LOG_ENABLED = False  # Disabled for tests
    CELERY_LOG_ENABLED = False  # Disabled for tests
    LOG_LEVEL = "INFO"
    LOG_DIR = "logs"
    LOG_FILE = "bayanat.log"
    LOG_BACKUP_COUNT = 5

    # Backups (disabled for tests)
    BACKUPS = False
    BACKUP_INTERVAL = 1
    BACKUPS_LOCAL_PATH = "backups/"
    BACKUPS_S3_BUCKET = None
    BACKUPS_AWS_ACCESS_KEY_ID = None
    BACKUPS_AWS_SECRET_ACCESS_KEY = None
    BACKUPS_AWS_REGION = None

    @classmethod
    def get(cls, key, default=None):
        """
        Smart config getter that automatically uses Flask app context when available.

        In Flask app context (requests/tests): uses current_app.config
        Outside app context (CLI/standalone): uses TestConfig class attributes

        Args:
            key: Configuration key name
            default: Default value if not found

        Returns:
            Configuration value
        """
        if has_app_context():
            return current_app.config.get(key, default)
        else:
            return getattr(cls, key, default)
