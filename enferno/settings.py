# -*- coding: utf-8 -*-
import os, redis

os_env = os.environ


class Config(object):
    SECRET_KEY = 'r@nd0mS3cr3t1' # Generate a new secret key
    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    DEBUG_TB_ENABLED = False  # Disable Debug toolbar
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    CACHE_TYPE = 'simple'  # Can be "memcached", "redis", etc.
    # database uri
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'SQLALCHEMY_DATABASE_URI', 'postgresql:///sjac')
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    CELERY_BROKER_URL = os.environ.get(
        'CELERY_BROKER_URL', 'redis://localhost:6379/10')
    REDIS_BULK_DB = 11
    CELERY_RESULT_BACKEND = os.environ.get(
        'CELERY_RESULT_BACKEND', 'redis://localhost:6379/{}'.format(REDIS_BULK_DB))


    # security
    SECURITY_REGISTERABLE = False
    SECURITY_RECOVERABLE = False
    SECURITY_CONFIRMABLE = False
    SECURITY_TRACKABLE = True
    SECURITY_PASSWORD_HASH = 'bcrypt'
    SECURITY_PASSWORD_SALT = 'nd0mS3cr3t2' # Generate a new password salt

    SECURITY_POST_LOGIN_VIEW = '/dashboard/'
    SECURITY_POST_CONFIRM_VIEW = '/dashboard/'

    SECURITY_TWO_FACTOR_ENABLED_METHODS= ['authenticator']  # 'sms' also valid but requires an sms provider
    SECURITY_TWO_FACTOR = True
    SECURITY_TWO_FACTOR_RESCUE_MAIL = ''


    # Generate a good totp secret using: passlib.totp.generate_secret()
    SECURITY_TOTP_SECRETS = {"1": "nd0mS3cr3t3"} # Generate a new totp secret
    SECURITY_TOTP_ISSUER = 'Bayanat'

    # get from https://www.google.com/recaptcha/admin
    RECAPTCHA_ENABLED = False
    RECAPTCHA_PUBLIC_KEY = 'ReCaptchaKey'
    RECAPTCHA_PRIVATE_KEY = 'ReCaptchaSecret'

    SESSION_TYPE = 'redis'
    SESSION_REDIS = redis.from_url(os.environ.get('SESSION_REDIS', 'redis://localhost:6379/1'))
    PERMANENT_SESSION_LIFETIME = 3600


    # flask mail settings
    MAIL_SERVER = 'smtp.domain.com'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USERNAME = 'user'
    MAIL_PASSWORD = 'pass'
    SECURITY_EMAIL_SENDER = 'info@domain.com'

    # get from https://console.cloud.google.com/
    GOOGLE_CLIENT_ID = os.environ.get(
        "GOOGLE_CLIENT_ID", 'ClientID')
    GOOGLE_CLIENT_SECRET = os.environ.get(
        "GOOGLE_CLIENT_SECRET", 'ClientSecret')
    GOOGLE_DISCOVERY_URL = (
        "https://accounts.google.com/.well-known/openid-configuration"
    )

    # File Upload Settings: switch to True to store files privately within the enferno/media directory
    FILESYSTEM_LOCAL = True

    # S3 settings
    # Bucket needs to be private with public access blocked 

    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', 'AWSACCESSKEY')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', 'AWSACCESSSECRET')
    S3_BUCKET = os.environ.get('S3_BUCKET','AWSBUCKET')

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



    # Cors Policy required on the bucket; Allowed Origin can be set to the domain of the system

    ''' 
    <?xml version="1.0" encoding="UTF-8"?>
    <CORSConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
    <CORSRule>
    <AllowedOrigin>*</AllowedOrigin>
    <AllowedMethod>GET</AllowedMethod>
    <AllowedHeader>*</AllowedHeader>
    </CORSRule>
    </CORSConfiguration>
    '''

    # Permissions Policy required for the bucket (replace bucket with the actual name); 

    '''
    {
    "Version": "2012-10-20",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::bucket"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject"
            ],
            "Resource": [
                "arn:aws:s3:::bucket/*"
            ]
            }
        ]
    }
    '''






# override configurations for production
class ProdConfig(Config):
    """Production configuration."""
    ENV = 'prod'
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'postgresql://user:pass@host/db'
    DEBUG_TB_ENABLED = False  # Disable Debug toolbar

# override configurations for development
class DevConfig(Config):
    """Development configuration."""
    ENV = 'dev'
    DEBUG = True
    DEBUG_TB_ENABLED = True
    CACHE_TYPE = 'simple'  # Can be "memcached", "redis", etc.
