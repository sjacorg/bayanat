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



    SECRET_KEY = os.environ.get('SECRET_KEY')
    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    DEBUG_TB_ENABLED = False  # Disable Debug toolbar
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    CACHE_TYPE = 'simple'  # Can be "memcached", "redis", etc.

    # Databaset 
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Celery
    celery_broker_url = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/10')
    REDIS_BULK_DB = 11
    result_backend = os.environ.get('result_backend', 'redis://localhost:6379/{}'.format(REDIS_BULK_DB))


    # Security
    SECURITY_REGISTERABLE = False
    SECURITY_RECOVERABLE = False
    SECURITY_CONFIRMABLE = False
    SECURITY_TRACKABLE = True
    SECURITY_PASSWORD_HASH = 'bcrypt'
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT')
    SECURITY_POST_LOGIN_VIEW = '/dashboard/'
    SECURITY_POST_CONFIRM_VIEW = '/dashboard/'

    SECURITY_USER_IDENTITY_ATTRIBUTES = [{"username": {"mapper": uia_username_mapper, "case_insensitive": True}}]

    #disabel token apis
    SECURITY_API_ENABLED_METHODS = ['session']

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

    # Reaphtcha
    RECAPTCHA_ENABLED = (os.environ.get('RECAPTCHA_ENABLED', 'False') == 'True')
    RECAPTCHA_PUBLIC_KEY = os.environ.get('RECAPTCHA_PUBLIC_KEY')
    RECAPTCHA_PRIVATE_KEY = os.environ.get('RECAPTCHA_PRIVATE_KEY')

    # Redis
    SESSION_TYPE = 'redis'
    SESSION_REDIS = redis.from_url(os.environ.get('SESSION_REDIS', 'redis://localhost:6379/1'))
    PERMANENT_SESSION_LIFETIME = 3600


    # flask mail settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    SECURITY_EMAIL_SENDER = os.environ.get('SECURITY_EMAIL_SENDER')

    # Google 0Auth
    GOOGLE_CLIENT_ID = os.environ.get(
        "GOOGLE_CLIENT_ID", '')
    GOOGLE_CLIENT_SECRET = os.environ.get(
        "GOOGLE_CLIENT_SECRET", '')
    GOOGLE_DISCOVERY_URL = (
        "https://accounts.google.com/.well-known/openid-configuration"
    )

    # File Upload Settings: switch to True to store files privately within the enferno/media directory
    FILESYSTEM_LOCAL = (os.environ.get('FILESYSTEM_LOCAL', 'False') == 'True')

    # Enable data import tool
    ETL_TOOL = (os.environ.get('ETL_TOOL', 'False') == 'True')

    # Enable data deduplication tool
    DEDUP_TOOL = (os.environ.get('DEDUP_TOOL', 'False') == 'True')

    # Valid video extension list (will be processed during ETL)
    ETL_VID_EXT = ["webm", "mkv", "flv", "vob", "ogv", "ogg", "rrc", "gifv", "mng", "mov", "avi", "qt", "wmv", "yuv", "rm", "asf", "amv", "mp4", "m4p", "m4v", "mpg", "mp2", "mpeg", "mpe", "mpv", "m4v", "svi", "3gp", "3g2", "mxf", "roq", "nsv", "flv", "f4v", "f4p", "f4a", "f4b", "mts", "lvr", "m2ts"]

    # S3 settings
    # Bucket needs to be private with public access blocked 
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    S3_BUCKET = os.environ.get('S3_BUCKET')
    AWS_REGION = os.environ.get('AWS_REGION')

    # i18n
    LANGUAGES = ['en', 'ar', 'uk']
    DEFAULT_LANGUAGE = os.environ.get('DEFAULT_LANGUAGE','en')
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

class DevConfig(Config):
    """Development configuration."""
    ENV = 'dev'
    DEBUG = True
    DEBUG_TB_ENABLED = True
    CACHE_TYPE = 'simple'  # Can be "memcached", "redis", etc.