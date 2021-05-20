# -*- coding: utf-8 -*-
import os, redis

os_env = os.environ


class Config(object):
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
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/10')
    REDIS_BULK_DB = 11
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/{}'.format(REDIS_BULK_DB))


    # Security
    SECURITY_REGISTERABLE = False
    SECURITY_RECOVERABLE = False
    SECURITY_CONFIRMABLE = False
    SECURITY_TRACKABLE = True
    SECURITY_PASSWORD_HASH = 'bcrypt'
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT')
    SECURITY_POST_LOGIN_VIEW = '/dashboard/'
    SECURITY_POST_CONFIRM_VIEW = '/dashboard/'

    SECURITY_TWO_FACTOR_ENABLED_METHODS= ['authenticator']  # 'sms' also valid but requires an sms provider
    SECURITY_TWO_FACTOR = os.environ.get('SECURITY_TWO_FACTOR')
    SECURITY_TWO_FACTOR_RESCUE_MAIL = os.environ.get('SECURITY_TWO_FACTOR_RESCUE_MAIL')

    # Block security auth tokens
    SECURITY_TOKEN_MAX_AGE = 0

    # 2fa
    SECURITY_TOTP_SECRETS = {"1": os.environ.get('SECURITY_TOTP_SECRETS')}
    SECURITY_TOTP_ISSUER = 'Bayanat'

    # Reaphtcha
    RECAPTCHA_ENABLED = False
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
    FILESYSTEM_LOCAL = True

    # Enable data import tool
    ETL_TOOL = True

    # Valid video extension list (will be processed during ETL)
    ETL_VID_EXT = ["webm", "mkv", "flv", "vob", "ogv", "ogg", "rrc", "gifv", "mng", "mov", "avi", "qt", "wmv", "yuv", "rm", "asf", "amv", "mp4", "m4p", "m4v", "mpg", "mp2", "mpeg", "mpe", "mpv", "m4v", "svi", "3gp", "3g2", "mxf", "roq", "nsv", "flv", "f4v", "f4p", "f4a", "f4b", "mts", "lvr", "m2ts"]

    # S3 settings
    # Bucket needs to be private with public access blocked 
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    S3_BUCKET = os.environ.get('S3_BUCKET')

    # i18n
    LANGUAGES = ['en', 'ar']
    # extract messages with the following command
    # pybabel extract -F babel.cfg -k _l -o messages.pot .
    # generate a new language using the following command
    # pybabel init -i messages.pot -d enferno/translations -l ar
    # to update existing translations
    # pybabel update -i messages.pot -d enferno/translations
    # compile translation using the following
    # pybabel compile -d enferno/translations

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