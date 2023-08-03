# -*- coding: utf-8 -*-
import os, redis
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()

os_env = os.environ
import bleach

class Config(object):

    def uia_username_mapper(identity):
        # we allow pretty much anything - but we bleach it.

        return bleach.clean(identity, strip=True)

    BASE_URL = os.environ.get('BASE_URL', 'http://127.0.0.1:5000/')

    SECRET_KEY = os.environ.get('SECRET_KEY')
    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    DEBUG_TB_ENABLED = False  # Disable Debug toolbar
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    CACHE_TYPE = 'simple'  # Can be "memcached", "redis", etc.

    # Databaset 
    # SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    POSTGRES_USER = os.environ.get('POSTGRES_USER', '')
    POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', '')
    POSTGRES_DB = os.environ.get('POSTGRES_DB', 'bayanat')
    POSTGRES_HOST = os.environ.get('POSTGRES_HOST', 'localhost')

    if (POSTGRES_USER and POSTGRES_PASSWORD) or POSTGRES_HOST != 'localhost':
        SQLALCHEMY_DATABASE_URI = F'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}'
    else: 
        SQLALCHEMY_DATABASE_URI = F'postgresql:///{POSTGRES_DB}'

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', '')
    REDIS_URL = F'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:6379/0'

    # Celery
    # Has to be in small case
    celery_broker_url = F'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:6379/2'
    result_backend = F'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:6379/3'


    # Security
    SECURITY_REGISTERABLE = False
    SECURITY_RECOVERABLE = False
    SECURITY_CONFIRMABLE = False
    SECURITY_CHANGEABLE = True
    SECURITY_SEND_PASSWORD_CHANGE_EMAIL = False
    SECURITY_TRACKABLE = True
    SECURITY_PASSWORD_HASH = 'bcrypt'
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT')
    SECURITY_POST_LOGIN_VIEW = '/dashboard/'
    SECURITY_POST_CONFIRM_VIEW = '/dashboard/'

    SECURITY_USER_IDENTITY_ATTRIBUTES = [{"username": {"mapper": uia_username_mapper, "case_insensitive": True}}]
    SECURITY_USERNAME_ENABLE = True

    SECURITY_MULTI_FACTOR_RECOVERY_CODES = True
    SECURITY_MULTI_FACTOR_RECOVERY_CODES_N = 3
    SECURITY_MULTI_FACTOR_RECOVERY_CODES_KEYS = None
    SECURITY_MULTI_FACTOR_RECOVERY_CODE_TTL = None

    # Disable token apis

    SECURITY_TWO_FACTOR_ENABLED_METHODS= ['authenticator']  # 'sms' also valid but requires an sms provider
    SECURITY_TWO_FACTOR = os.environ.get('SECURITY_TWO_FACTOR')
    SECURITY_TWO_FACTOR_RESCUE_MAIL = os.environ.get('SECURITY_TWO_FACTOR_RESCUE_MAIL')

    # Enable only session auth
    SECURITY_API_ENABLED_METHODS = ['session']
    SECURITY_FRESHNESS = timedelta(hours=6)
    SECURITY_FRESHNESS_GRACE_PERIOD = timedelta(minutes=30)

    # Strong session protection
    SESSION_PROTECTION = 'strong'

    # 2fa
    SECURITY_TOTP_SECRETS = {"1": os.environ.get('SECURITY_TOTP_SECRETS')}
    SECURITY_TOTP_ISSUER = 'Bayanat'

    # Recaptcha
    RECAPTCHA_ENABLED = (os.environ.get('RECAPTCHA_ENABLED', 'False') == 'True')
    RECAPTCHA_PUBLIC_KEY = os.environ.get('RECAPTCHA_PUBLIC_KEY')
    RECAPTCHA_PRIVATE_KEY = os.environ.get('RECAPTCHA_PRIVATE_KEY')

    # Session
    SESSION_TYPE = 'redis'
    SESSION_REDIS = redis.from_url(F'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:6379/1')
    PERMANENT_SESSION_LIFETIME = 3600

    # Google 0Auth
    GOOGLE_CLIENT_ID = os.environ.get(
        "GOOGLE_CLIENT_ID", '')
    GOOGLE_CLIENT_SECRET = os.environ.get(
        "GOOGLE_CLIENT_SECRET", '')
    GOOGLE_DISCOVERY_URL = (
        "https://accounts.google.com/.well-known/openid-configuration"
    )

    GOOGLE_CLIENT_ALLOWED_DOMAIN = os.environ.get('GOOGLE_CLIENT_ALLOWED_DOMAIN', 'gmail.com')

    # File Upload Settings: switch to True to store files privately within the enferno/media directory
    FILESYSTEM_LOCAL = (os.environ.get('FILESYSTEM_LOCAL', 'False') == 'True')

    # Enable data import tool
    ETL_TOOL = (os.environ.get('ETL_TOOL', 'False') == 'True')
    ETL_PATH_IMPORT = (os.environ.get('ETL_PATH_IMPORT', 'False') == 'True')
    ETL_ALLOWED_PATH = os.environ.get('ETL_ALLOWED_PATH', None)

    EXPORT_TOOL = (os.environ.get('EXPORT_TOOL', 'False') == 'True')
    # Export file expiry in seconds (2 hours)
    EXPORT_DEFAULT_EXPIRY = int(os.environ.get('EXPORT_DEFAULT_EXPIRY', 7200))
    # Enable data deduplication tool
    DEDUP_TOOL = (os.environ.get('DEDUP_TOOL', 'False') == 'True')

    # Valid video extension list (will be processed during ETL)
    ETL_VID_EXT = ["webm", "mkv", "flv", "vob", "ogv", "ogg", "rrc", "gifv", "mng", "mov", "avi", "qt", "wmv", "yuv", "rm", "asf", "amv", "mp4", "m4p", "m4v", "mpg", "mp2", "mpeg", "mpe", "mpv", "m4v", "svi", "3gp", "3g2", "mxf", "roq", "nsv", "flv", "f4v", "f4p", "f4a", "f4b", "mts", "lvr", "m2ts"]

    # valid image extenstions supported by Tesseract OCR
    OCR_ENABLED = (os.environ.get('OCR_ENABLED', 'False') == 'True')
    OCR_EXT = ["png", "jpeg", "tiff", "jpg", "gif", "webp", "bmp" ,"pnm"]
    TESSERACT_CMD = os.environ.get('TESSERACT_CMD', r'/usr/bin/tesseract')

    # Allowed file upload extensions
    MEDIA_ALLOWED_EXTENSIONS = ['.' + ext for ext in ETL_VID_EXT] + ['.' + ext for ext in OCR_EXT] + ['.pdf', '.docx']
    SHEETS_ALLOWED_EXTENSIONS = ['.csv', '.xls', '.xlsx']

    # S3 settings
    # Bucket needs to be private with public access blocked 
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    S3_BUCKET = os.environ.get('S3_BUCKET')
    AWS_REGION = os.environ.get('AWS_REGION')

    # i18n
    LANGUAGES = ['en', 'ar', 'uk', 'fr']
    BABEL_DEFAULT_LOCALE = os.environ.get('DEFAULT_LANGUAGE','en')
    # extract messages with the following command
    # pybabel extract -F babel.cfg -k _l -o messages.pot .
    # generate a new language using the following command
    # pybabel init -i messages.pot -d enferno/translations -l ar
    # to update existing translations
    # pybabel update -i messages.pot -d enferno/translations
    # compile translation using the following
    # pybabel compile -d enferno/translations

    MAPS_API_ENDPOINT = os.environ.get('MAPS_API_ENDPOINT', 'https://{s}.tile.osm.org/{z}/{x}/{y}.png')
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')

    # Missing persons
    MISSING_PERSONS = (os.environ.get('MISSING_PERSONS', 'False') == 'True')

    # Deduplication

    # specify min and max distance for matching
    DEDUP_LOW_DISTANCE = float(os.environ.get('DEDUP_LOW_DISTANCE', 0.3))
    DEDUP_MAX_DISTANCE = float(os.environ.get('DEDUP_MAX_DISTANCE', 0.5))

    # how many items to process every cycle (cycles are processed based on the time interval below)
    DEDUP_BATCH_SIZE = int(os.environ.get('DEDUP_BATCH_SIZE',30))

    # the time in seconds at which a batch of deduplication items is processed
    DEDUP_INTERVAL = 3

    #Sheet import tool settings
    SHEET_IMPORT = (os.environ.get('SHEET_IMPORT', 'False') == 'True')
    IMPORT_DIR = 'enferno/imports'


class ProdConfig(Config):
    """Production configuration."""
    ENV = 'prod'
    DEBUG = False
    DEBUG_TB_ENABLED = False  # Disable Debug toolbar

    # secure cookies (flask core)
    SESSION_COOKIE_SECURE = os.environ.get('SECURE_COOKIES', 'True') == 'True'
    REMEMBER_COOKIE_SECURE = os.environ.get('SECURE_COOKIES', 'True') == 'True'
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # flask-security cookie
    SECURITY_CSRF_COOKIE ={
        # Overrides default secure = False to require HTTPS.
        "samesite": "Strict", "httponly": False, "secure": os.environ.get('SECURE_COOKIES', 'True') == 'True'
    }

class DevConfig(Config):
    """Development configuration."""
    ENV = 'dev'
    DEBUG = True
    DEBUG_TB_ENABLED = True
    CACHE_TYPE = 'simple'  # Can be "memcached", "redis", etc.