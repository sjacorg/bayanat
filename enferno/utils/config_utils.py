import json
from types import MappingProxyType
from flask_security import current_user

class ConfigManager:
    CONFIG_FILE_PATH = 'config.json'
    MASK_STRING = '**********'
    config = {}

    # Define default core configurations here
    DEFAULT_CONFIG = MappingProxyType({
        # timedelta type
        'SECURITY_FRESHNESS': 30,
        'SECURITY_FRESHNESS_GRACE_PERIOD': 30,

        'RECAPTCHA_ENABLED': False,
        'RECAPTCHA_PUBLIC_KEY': '',
        'RECAPTCHA_PRIVATE_KEY': '',

        'GOOGLE_CLIENT_ID': '',
        'GOOGLE_CLIENT_SECRET': '',
        'GOOGLE_DISCOVERY_URL': 'https://accounts.google.com/.well-known/openid-configuration',

        'FILESYSTEM_LOCAL': 1,

        'AWS_ACCESS_KEY_ID': '',
        'AWS_SECRET_ACCESS_KEY': '',
        'S3_BUCKET': '',
        'AWS_REGION': '',

        'MEDIA_ALLOWED_EXTENSIONS': [".mp4", ".webm", ".jpg", ".gif", ".png", ".pdf", ".doc", ".txt"],
        'MEDIA_UPLOAD_MAX_FILE_SIZE': 1000,

        'SHEETS_ALLOWED_EXTENSIONS': ["csv", "xls", "xlsx"],

        'ETL_TOOL': False,
        'ETL_PATH_IMPORT': False,
        'ETL_VID_EXT': ["webm", "mkv", "flv", "vob", "ogv", "ogg", "rrc", "gifv", "mng", "mov", "avi", "qt", "wmv",
                        "yuv", "rm", "asf", "amv", "mp4", "m4p", "m4v", "mpg", "mp2", "mpeg", "mpe", "mpv", "m4v",
                        "svi", "3gp", "3g2", "mxf", "roq", "nsv", "flv", "f4v", "f4p", "f4a", "f4b", "mts", "lvr",
                        "m2ts"],

        'OCR_ENABLED': False,
        'OCR_EXT': ["png", "jpeg", "tiff", "jpg", "gif", "webp", "bmp", "pnm"],
        'TESSERACT_CMD': '/usr/bin/tesseract',

        'SHEET_IMPORT': False,

        'DEDUP_TOOL': False,

        'LANGUAGES': ["en", "ar", "uk", 'fr'],
        'BABEL_DEFAULT_LOCALE': "en",

        'MAPS_API_ENDPOINT': 'https://{s}.tile.osm.org/{z}/{x}/{y}.png',
        'GOOGLE_MAPS_API_KEY': '',

        'MISSING_PERSONS': False,

        'DEDUP_LOW_DISTANCE': 0.3,
        'DEDUP_MAX_DISTANCE': 0.5,
        'DEDUP_BATCH_SIZE': 30,
        'DEDUP_INTERVAL': 3,

        'GEO_MAP_DEFAULT_CENTER': {'lat': 33.510414,
                                   'lng': 36.278336
                                   },

        'ITEMS_PER_PAGE_OPTIONS': [10, 30, 100],

        'VIDEO_RATES': [0.25, 0.5, 1, 1.5, 2, 4],

        'EXPORT_TOOL': False
    })

    CONFIG_LABELS = MappingProxyType({
        # timedelta type
        'SECURITY_FRESHNESS': 'Security Freshness',
        'SECURITY_FRESHNESS_GRACE_PERIOD': 'Security Freshness Grace Period',

        'RECAPTCHA_ENABLED': 'Recaptcha Enabled',
        'RECAPTCHA_PUBLIC_KEY': 'Recaptcha Public Key',
        'RECAPTCHA_PRIVATE_KEY': 'Recaptcha Private Key',

        'GOOGLE_CLIENT_ID': 'Google Client Id',
        'GOOGLE_CLIENT_SECRET': 'Google Client Secret',
        'GOOGLE_DISCOVERY_URL': 'Google Discovery Url',

        'FILESYSTEM_LOCAL': 'Filesystem Local',

        'AWS_ACCESS_KEY_ID': 'Aws Access Key Id',
        'AWS_SECRET_ACCESS_KEY': 'Aws Secret Access Key',
        'S3_BUCKET': 'S3 Bucket',
        'AWS_REGION': 'Aws Region',

        'MEDIA_ALLOWED_EXTENSIONS': 'Media Allowed Extensions',
        'MEDIA_UPLOAD_MAX_FILE_SIZE': 'Media Maximum File Upload Size',


        'SHEETS_ALLOWED_EXTENSIONS': 'Sheets Allowed Extensions',

        'ETL_TOOL': 'Etl Tool',
        'ETL_PATH_IMPORT': 'Etl Path Import',
        'ETL_VID_EXT': 'Etl Vid Ext',

        'OCR_ENABLED': 'Ocr Enabled',
        'OCR_EXT': 'Ocr Ext',
        'TESSERACT_CMD': 'Tesseract Cmd',

        'SHEET_IMPORT': 'Sheet Import',

        'DEDUP_TOOL': 'Dedup Tool',

        'LANGUAGES': 'Languages',
        'BABEL_DEFAULT_LOCALE': 'Babel Default Locale',

        'MAPS_API_ENDPOINT': 'Maps Api Endpoint',
        'GOOGLE_MAPS_API_KEY': 'Google Maps Api Key',

        'MISSING_PERSONS': 'Missing Persons',

        'DEDUP_LOW_DISTANCE': 'Dedup Low Distance',
        'DEDUP_MAX_DISTANCE': 'Dedup Low Distance',
        'DEDUP_BATCH_SIZE': 'Dedup Batch Size',
        'DEDUP_INTERVAL': 'Dedup Interval',

        'GEO_MAP_DEFAULT_CENTER_LAT': 'Geo Map Default Center Lat',
        'GEO_MAP_DEFAULT_CENTER_LNG': 'Geo Map Default Center Lng',

        'ITEMS_PER_PAGE_OPTIONS': 'Items Per Page Options',

        'VIDEO_RATES': 'Video Rates',

        'EXPORT_TOOL': 'Export Tool'
    })

    def __init__(self):
        try:
            with open(self.CONFIG_FILE_PATH) as file:
                self.config = json.loads(file.read())
        except EnvironmentError:
            print("No config file found, Loading default Bayanat configurations")

    def get_config(self, cfg):
        # custom getter with a fallback
        value = self.config.get(cfg)
        # Also implement fallback if dict key exists but is null/false/empty
        if value is not None:
            return value
        else:
            return ConfigManager.DEFAULT_CONFIG.get(cfg)

    @staticmethod
    def serialize():
        from enferno.settings import Config as cfg

        conf = {
            # timedelta type
            'SECURITY_FRESHNESS': int(cfg.SECURITY_FRESHNESS.total_seconds())/60,
            'SECURITY_FRESHNESS_GRACE_PERIOD': int(cfg.SECURITY_FRESHNESS_GRACE_PERIOD.total_seconds())/60,

            'RECAPTCHA_ENABLED': cfg.RECAPTCHA_ENABLED,
            'RECAPTCHA_PUBLIC_KEY': cfg.RECAPTCHA_PUBLIC_KEY,
            'RECAPTCHA_PRIVATE_KEY': cfg.RECAPTCHA_PRIVATE_KEY,

            'GOOGLE_CLIENT_ID': cfg.GOOGLE_CLIENT_ID,
            'GOOGLE_CLIENT_SECRET': cfg.GOOGLE_CLIENT_SECRET,
            'GOOGLE_DISCOVERY_URL': cfg.GOOGLE_DISCOVERY_URL,

            'FILESYSTEM_LOCAL': cfg.FILESYSTEM_LOCAL,

            'AWS_ACCESS_KEY_ID': cfg.AWS_ACCESS_KEY_ID,
            'AWS_SECRET_ACCESS_KEY': ConfigManager.MASK_STRING if cfg.AWS_SECRET_ACCESS_KEY else '',
            'S3_BUCKET': cfg.S3_BUCKET,
            'AWS_REGION': cfg.AWS_REGION,

            'MEDIA_ALLOWED_EXTENSIONS': cfg.MEDIA_ALLOWED_EXTENSIONS,
            'MEDIA_UPLOAD_MAX_FILE_SIZE': cfg.MEDIA_UPLOAD_MAX_FILE_SIZE,
            'SHEETS_ALLOWED_EXTENSIONS': cfg.SHEETS_ALLOWED_EXTENSIONS,

            'ETL_TOOL': cfg.ETL_TOOL,
            'ETL_PATH_IMPORT': cfg.ETL_PATH_IMPORT,
            'ETL_VID_EXT': cfg.ETL_VID_EXT,

            'OCR_ENABLED': cfg.OCR_ENABLED,
            'OCR_EXT': cfg.OCR_EXT,
            'TESSERACT_CMD': cfg.TESSERACT_CMD,

            'SHEET_IMPORT': cfg.SHEET_IMPORT,

            'DEDUP_TOOL': cfg.DEDUP_TOOL,

            'LANGUAGES': cfg.LANGUAGES,
            'BABEL_DEFAULT_LOCALE': cfg.BABEL_DEFAULT_LOCALE,

            'MAPS_API_ENDPOINT': cfg.MAPS_API_ENDPOINT,
            'GOOGLE_MAPS_API_KEY': cfg.GOOGLE_MAPS_API_KEY,

            'MISSING_PERSONS': cfg.MISSING_PERSONS,

            'DEDUP_LOW_DISTANCE': cfg.DEDUP_LOW_DISTANCE,
            'DEDUP_MAX_DISTANCE': cfg.DEDUP_MAX_DISTANCE,
            'DEDUP_BATCH_SIZE': cfg.DEDUP_BATCH_SIZE,
            'DEDUP_INTERVAL': cfg.DEDUP_INTERVAL,

            'GEO_MAP_DEFAULT_CENTER': {
                'lat': cfg.GEO_MAP_DEFAULT_CENTER_LAT,
                'lng': cfg.GEO_MAP_DEFAULT_CENTER_LNG
            },
             
            'ITEMS_PER_PAGE_OPTIONS': cfg.ITEMS_PER_PAGE_OPTIONS,

            'VIDEO_RATES': cfg.VIDEO_RATES,

            'EXPORT_TOOL': cfg.EXPORT_TOOL
        }
        return conf

    @staticmethod
    def validate(conf):
        return True

    @staticmethod
    def write_config(conf):
        from enferno.tasks import reload_app
        from enferno.admin.models import AppConfig, Activity
        # handle secrets
        from enferno.settings import Config as cfg
        if conf.get('AWS_SECRET_ACCESS_KEY') == ConfigManager.MASK_STRING:
            # Keep existing secret
            conf['AWS_SECRET_ACCESS_KEY'] = cfg.AWS_SECRET_ACCESS_KEY

        if ConfigManager.validate(conf):
            try:
                # write config version to db
                app_config = AppConfig()
                app_config.config = conf
                app_config.user_id = current_user.id
                app_config.save()

                # record activity
                Activity.create(current_user, Activity.ACTION_CREATE,app_config.to_mini(), 'config')

                with open(ConfigManager.CONFIG_FILE_PATH, 'w') as f:
                    f.write(json.dumps(conf, indent=2))
                    # attempt app reload
                    reload_app()
                    return True

            except Exception as e:
                print(e)

        return False
