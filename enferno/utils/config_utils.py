import json
from types import MappingProxyType
from flask_security import current_user

import logging
import os
import shutil
from enferno.admin.constants import Constants
from enferno.utils.notification_config import NOTIFICATIONS_CONFIG

NotificationEvent = Constants.NotificationEvent

logger = logging.getLogger("app_logger")


class ConfigManager:
    CONFIG_FILE_PATH = "config.json"
    MASK_STRING = "**********"
    config = {}

    # Define default core configurations here
    DEFAULT_CONFIG = MappingProxyType(
        {
            # timedelta type
            "SECURITY_FRESHNESS": 30,
            "SECURITY_FRESHNESS_GRACE_PERIOD": 30,
            "SECURITY_TWO_FACTOR_REQUIRED": False,
            "SECURITY_PASSWORD_LENGTH_MIN": 10,
            "SECURITY_ZXCVBN_MINIMUM_SCORE": 3,
            "DISABLE_MULTIPLE_SESSIONS": True,
            "SESSION_RETENTION_PERIOD": 30,
            "RECAPTCHA_ENABLED": False,
            "RECAPTCHA_PUBLIC_KEY": "",
            "RECAPTCHA_PRIVATE_KEY": "",
            "GOOGLE_OAUTH_ENABLED": False,
            "GOOGLE_CLIENT_ID": "",
            "GOOGLE_CLIENT_SECRET": "",
            "GOOGLE_DISCOVERY_URL": "https://accounts.google.com/.well-known/openid-configuration",
            "FILESYSTEM_LOCAL": 1,
            "AWS_ACCESS_KEY_ID": "",
            "AWS_SECRET_ACCESS_KEY": "",
            "S3_BUCKET": "",
            "AWS_REGION": "",
            "ACCESS_CONTROL_RESTRICTIVE": False,
            "AC_USERS_CAN_RESTRICT_NEW": False,
            "MEDIA_ALLOWED_EXTENSIONS": [
                "mp4",
                "webm",
                "jpg",
                "gif",
                "png",
                "pdf",
                "doc",
                "txt",
            ],
            "MEDIA_UPLOAD_MAX_FILE_SIZE": 1000,
            "SHEETS_ALLOWED_EXTENSIONS": ["csv", "xls", "xlsx"],
            "ETL_TOOL": False,
            "ETL_PATH_IMPORT": False,
            "ETL_VID_EXT": [
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
                "m4v",
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
            ],
            "OCR_ENABLED": False,
            "OCR_EXT": ["png", "jpeg", "tiff", "jpg", "gif", "webp", "bmp", "pnm"],
            "SHEET_IMPORT": False,
            "DEDUP_TOOL": False,
            "BABEL_DEFAULT_LOCALE": "en",
            "MAPS_API_ENDPOINT": "https://{s}.tile.osm.org/{z}/{x}/{y}.png",
            "GOOGLE_MAPS_API_KEY": "",
            "DEDUP_LOW_DISTANCE": 0.3,
            "DEDUP_MAX_DISTANCE": 0.5,
            "DEDUP_BATCH_SIZE": 30,
            "DEDUP_INTERVAL": 3,
            "GEO_MAP_DEFAULT_CENTER": {"lat": 33.510414, "lng": 36.278336, "radius": 1000},
            "ITEMS_PER_PAGE_OPTIONS": [10, 30, 100],
            "VIDEO_RATES": [0.25, 0.5, 1, 1.5, 2, 4],
            "EXPORT_TOOL": False,
            "EXPORT_DEFAULT_EXPIRY": 2,
            "ACTIVITIES": {
                "APPROVE": True,
                "BULK": True,
                "CREATE": True,
                "DELETE": True,
                "DOWNLOAD": True,
                "LOGIN": True,
                "LOGOUT": True,
                "REVIEW": True,
                "REJECT": True,
                "REQUEST": True,
                "SEARCH": True,
                "SELF-ASSIGN": True,
                "UPDATE": True,
                "UPLOAD": True,
                "VIEW": True,
            },
            "ACTIVITIES_RETENTION": 90,
            "ADV_ANALYSIS": False,
            "LOCATIONS_INCLUDE_POSTAL_CODE": False,
            "MAIL_ENABLED": False,
            "MAIL_ALLOWED_DOMAINS": [],
            "MAIL_SERVER": "",
            "MAIL_PORT": 25,
            "MAIL_USE_TLS": False,
            "MAIL_USE_SSL": False,
            "MAIL_USERNAME": "",
            "MAIL_PASSWORD": "",
            "MAIL_DEFAULT_SENDER": "",
            "TRANSCRIPTION_ENABLED": False,
            "WHISPER_MODEL": "base",
            "WEB_IMPORT": False,
            "YTDLP_PROXY": "",
            "YTDLP_ALLOWED_DOMAINS": [
                "youtube.com",
                "facebook.com",
                "instagram.com",
                "twitter.com",
            ],
            "YTDLP_COOKIES": "",
            "NOTIFICATIONS": NOTIFICATIONS_CONFIG,  # Import from notification_config.py
        }
    )

    CONFIG_LABELS = MappingProxyType(
        {
            "SECURITY_FRESHNESS": "Security Freshness",
            "SECURITY_FRESHNESS_GRACE_PERIOD": "Security Freshness Grace Period",
            "SECURITY_TWO_FACTOR_REQUIRED": "Enforce 2FA User Enrollment",
            "SECURITY_PASSWORD_LENGTH_MIN": "Minimum Password Length",
            "SECURITY_ZXCVBN_MINIMUM_SCORE": "Password Strength Score",
            "DISABLE_MULTIPLE_SESSIONS": "Disable Multiple Sessions",
            "SESSION_RETENTION_PERIOD": "Session Retention Period",
            "RECAPTCHA_ENABLED": "Recaptcha Enabled",
            "RECAPTCHA_PUBLIC_KEY": "Recaptcha Public Key",
            "RECAPTCHA_PRIVATE_KEY": "Recaptcha Private Key",
            "GOOGLE_CLIENT_ID": "Google Client Id",
            "GOOGLE_CLIENT_SECRET": "Google Client Secret",
            "GOOGLE_DISCOVERY_URL": "Google Discovery Url",
            "FILESYSTEM_LOCAL": "Filesystem Local",
            "AWS_ACCESS_KEY_ID": "Aws Access Key Id",
            "AWS_SECRET_ACCESS_KEY": "Aws Secret Access Key",
            "S3_BUCKET": "S3 Bucket",
            "AWS_REGION": "Aws Region",
            "ACCESS_CONTROL_RESTRICTIVE": "Restrictive Access Control",
            "AC_USERS_CAN_RESTRICT_NEW": "Users Can Restrict New Items",
            "MEDIA_ALLOWED_EXTENSIONS": "Media Allowed Extensions",
            "MEDIA_UPLOAD_MAX_FILE_SIZE": "Media Maximum File Upload Size",
            "SHEETS_ALLOWED_EXTENSIONS": "Sheets Allowed Extensions",
            "ETL_TOOL": "Etl Tool",
            "ETL_PATH_IMPORT": "Etl Path Import",
            "ETL_VID_EXT": "Etl Vid Ext",
            "OCR_ENABLED": "Ocr Enabled",
            "OCR_EXT": "Ocr Ext",
            "SHEET_IMPORT": "Sheet Import",
            "DEDUP_TOOL": "Dedup Tool",
            "BABEL_DEFAULT_LOCALE": "Default System Language",
            "MAPS_API_ENDPOINT": "Maps Api Endpoint",
            "GOOGLE_MAPS_API_KEY": "Google Maps Api Key",
            "DEDUP_LOW_DISTANCE": "Dedup Low Distance",
            "DEDUP_MAX_DISTANCE": "Dedup Low Distance",
            "DEDUP_BATCH_SIZE": "Dedup Batch Size",
            "DEDUP_INTERVAL": "Dedup Interval",
            "GEO_MAP_DEFAULT_CENTER_LAT": "Geo Map Default Center Lat",
            "GEO_MAP_DEFAULT_CENTER_LNG": "Geo Map Default Center Lng",
            "GEO_MAP_DEFAULT_CENTER_RADIUS": "Geo Map Default Center Radius",
            "ITEMS_PER_PAGE_OPTIONS": "Items Per Page Options",
            "VIDEO_RATES": "Video Rates",
            "EXPORT_TOOL": "Export Tool",
            "EXPORT_DEFAULT_EXPIRY": "Export Default Expiry Time",
            "ACTIVITIES": "List of users activities to log.",
            "ACTIVITIES_RETENTION": "Activity Retention Period",
            "ADV_ANALYSIS": "Advanced Analysis Features",
            "LOCATIONS_INCLUDE_POSTAL_CODE": "Full Locations Include Postal Code",
            "MAIL_ENABLED": "Mail Enabled",
            "MAIL_ALLOWED_DOMAINS": "Allowed Mail Domains",
            "MAIL_SERVER": "Mail Server",
            "MAIL_PORT": "Mail Port",
            "MAIL_USE_TLS": "Mail Use TLS",
            "MAIL_USE_SSL": "Mail Use SSL",
            "MAIL_USERNAME": "Mail Username",
            "MAIL_PASSWORD": "Mail Password",
            "MAIL_DEFAULT_SENDER": "Mail Default Sender",
            "TRANSCRIPTION_ENABLED": "Allow Transcription of Media Files",
            "WHISPER_MODEL": "Whisper Model",
            "WEB_IMPORT": "Web Import",
            "YTDLP_PROXY": "Proxy URL to use with Web Import",
            "YTDLP_ALLOWED_DOMAINS": "Allowed Domains for Web Import",
            "YTDLP_COOKIES": "Cookies to use with Web Import",
            "NOTIFICATIONS": "Notification Events",
        }
    )

    def __init__(self):
        try:
            with open(self.CONFIG_FILE_PATH) as file:
                self.config = json.loads(file.read())
        except EnvironmentError:
            logger.error("No config file found, Loading default Bayanat configurations")

    def get_config(self, cfg):
        # custom getter with a fallback
        value = self.config.get(cfg)
        # Also implement fallback if dict key exists but is null/false/empty
        if value is not None:
            return value
        else:
            return ConfigManager.DEFAULT_CONFIG.get(cfg)

    @staticmethod
    def get_default_config(cfg):
        return ConfigManager.DEFAULT_CONFIG.get(cfg)

    @staticmethod
    def get_all_default_configs():
        default_configs = {
            entry: ConfigManager.get_default_config(entry) for entry in ConfigManager.DEFAULT_CONFIG
        }
        return default_configs

    @staticmethod
    def serialize():
        from enferno.settings import Config as cfg

        conf = {
            # timedelta type
            "SECURITY_FRESHNESS": int(cfg.SECURITY_FRESHNESS.total_seconds()) / 60,
            "SECURITY_FRESHNESS_GRACE_PERIOD": int(
                cfg.SECURITY_FRESHNESS_GRACE_PERIOD.total_seconds()
            )
            / 60,
            "SECURITY_TWO_FACTOR_REQUIRED": cfg.SECURITY_TWO_FACTOR_REQUIRED,
            "SECURITY_PASSWORD_LENGTH_MIN": cfg.SECURITY_PASSWORD_LENGTH_MIN,
            "SECURITY_ZXCVBN_MINIMUM_SCORE": cfg.SECURITY_ZXCVBN_MINIMUM_SCORE,
            "DISABLE_MULTIPLE_SESSIONS": cfg.DISABLE_MULTIPLE_SESSIONS,
            "SESSION_RETENTION_PERIOD": cfg.SESSION_RETENTION_PERIOD,
            "RECAPTCHA_ENABLED": cfg.RECAPTCHA_ENABLED,
            "RECAPTCHA_PUBLIC_KEY": cfg.RECAPTCHA_PUBLIC_KEY,
            "RECAPTCHA_PRIVATE_KEY": ConfigManager.MASK_STRING if cfg.RECAPTCHA_PRIVATE_KEY else "",
            "GOOGLE_OAUTH_ENABLED": cfg.GOOGLE_OAUTH_ENABLED,
            "GOOGLE_CLIENT_ID": cfg.GOOGLE_CLIENT_ID,
            "GOOGLE_CLIENT_SECRET": ConfigManager.MASK_STRING if cfg.GOOGLE_CLIENT_SECRET else "",
            "GOOGLE_DISCOVERY_URL": cfg.GOOGLE_DISCOVERY_URL,
            "FILESYSTEM_LOCAL": cfg.FILESYSTEM_LOCAL,
            "AWS_ACCESS_KEY_ID": cfg.AWS_ACCESS_KEY_ID,
            "AWS_SECRET_ACCESS_KEY": ConfigManager.MASK_STRING if cfg.AWS_SECRET_ACCESS_KEY else "",
            "S3_BUCKET": cfg.S3_BUCKET,
            "AWS_REGION": cfg.AWS_REGION,
            "ACCESS_CONTROL_RESTRICTIVE": cfg.ACCESS_CONTROL_RESTRICTIVE,
            "AC_USERS_CAN_RESTRICT_NEW": cfg.AC_USERS_CAN_RESTRICT_NEW,
            "MEDIA_ALLOWED_EXTENSIONS": cfg.MEDIA_ALLOWED_EXTENSIONS,
            "MEDIA_UPLOAD_MAX_FILE_SIZE": cfg.MEDIA_UPLOAD_MAX_FILE_SIZE,
            "SHEETS_ALLOWED_EXTENSIONS": cfg.SHEETS_ALLOWED_EXTENSIONS,
            "ETL_TOOL": cfg.ETL_TOOL,
            "ETL_PATH_IMPORT": cfg.ETL_PATH_IMPORT,
            "ETL_VID_EXT": cfg.ETL_VID_EXT,
            "OCR_ENABLED": cfg.OCR_ENABLED,
            "OCR_EXT": cfg.OCR_EXT,
            "SHEET_IMPORT": cfg.SHEET_IMPORT,
            "DEDUP_TOOL": cfg.DEDUP_TOOL,
            "BABEL_DEFAULT_LOCALE": cfg.BABEL_DEFAULT_LOCALE,
            "MAPS_API_ENDPOINT": cfg.MAPS_API_ENDPOINT,
            "GOOGLE_MAPS_API_KEY": cfg.GOOGLE_MAPS_API_KEY,
            "DEDUP_LOW_DISTANCE": cfg.DEDUP_LOW_DISTANCE,
            "DEDUP_MAX_DISTANCE": cfg.DEDUP_MAX_DISTANCE,
            "DEDUP_BATCH_SIZE": cfg.DEDUP_BATCH_SIZE,
            "DEDUP_INTERVAL": cfg.DEDUP_INTERVAL,
            "GEO_MAP_DEFAULT_CENTER": {
                "lat": cfg.GEO_MAP_DEFAULT_CENTER_LAT,
                "lng": cfg.GEO_MAP_DEFAULT_CENTER_LNG,
                "radius": cfg.GEO_MAP_DEFAULT_CENTER_RADIUS,
            },
            "ITEMS_PER_PAGE_OPTIONS": cfg.ITEMS_PER_PAGE_OPTIONS,
            "VIDEO_RATES": cfg.VIDEO_RATES,
            "EXPORT_TOOL": cfg.EXPORT_TOOL,
            "EXPORT_DEFAULT_EXPIRY": int(cfg.EXPORT_DEFAULT_EXPIRY.total_seconds()) / 3600,
            "ACTIVITIES": cfg.ACTIVITIES,
            "ACTIVITIES_RETENTION": int(cfg.ACTIVITIES_RETENTION.total_seconds()) / 86400,
            "ADV_ANALYSIS": cfg.ADV_ANALYSIS,
            "LOCATIONS_INCLUDE_POSTAL_CODE": cfg.LOCATIONS_INCLUDE_POSTAL_CODE,
            "MAIL_ENABLED": cfg.MAIL_ENABLED,
            "MAIL_ALLOWED_DOMAINS": cfg.MAIL_ALLOWED_DOMAINS,
            "MAIL_SERVER": cfg.MAIL_SERVER,
            "MAIL_PORT": cfg.MAIL_PORT,
            "MAIL_USE_TLS": cfg.MAIL_USE_TLS,
            "MAIL_USE_SSL": cfg.MAIL_USE_SSL,
            "MAIL_USERNAME": cfg.MAIL_USERNAME,
            "MAIL_PASSWORD": ConfigManager.MASK_STRING if cfg.MAIL_PASSWORD else "",
            "MAIL_DEFAULT_SENDER": cfg.MAIL_DEFAULT_SENDER,
            "TRANSCRIPTION_ENABLED": cfg.TRANSCRIPTION_ENABLED,
            "WHISPER_MODEL": cfg.WHISPER_MODEL,
            "WEB_IMPORT": cfg.WEB_IMPORT,
            "YTDLP_PROXY": cfg.YTDLP_PROXY or "",
            "YTDLP_ALLOWED_DOMAINS": cfg.YTDLP_ALLOWED_DOMAINS,
            "YTDLP_COOKIES": cfg.YTDLP_COOKIES or "",
            "NOTIFICATIONS": cfg.NOTIFICATIONS,
        }
        return conf

    @staticmethod
    def validate(conf):
        return True

    @staticmethod
    def write_config(conf):
        from enferno.admin.models import AppConfig, Activity

        # handle secrets
        from enferno.settings import Config as cfg

        if conf.get("AWS_SECRET_ACCESS_KEY") == ConfigManager.MASK_STRING:
            # Keep existing secret
            conf["AWS_SECRET_ACCESS_KEY"] = cfg.AWS_SECRET_ACCESS_KEY

        if conf.get("MAIL_PASSWORD") == ConfigManager.MASK_STRING:
            # Keep existing secret
            conf["MAIL_PASSWORD"] = cfg.MAIL_PASSWORD

        if ConfigManager.validate(conf):
            try:
                # write config version to db
                app_config = AppConfig()
                app_config.config = conf
                app_config.user_id = current_user.id
                app_config.save()

                # record activity
                Activity.create(
                    current_user,
                    Activity.ACTION_CREATE,
                    Activity.STATUS_SUCCESS,
                    app_config.to_mini(),
                    "config",
                )

                with open(ConfigManager.CONFIG_FILE_PATH, "w") as f:
                    f.write(json.dumps(conf, indent=2))
                    logger.info("New configuration saved.")

                return True

            except Exception:
                logger.error("Error writing new configuration.", exc_info=True)

        return False

    @staticmethod
    def restore_default_config():
        """
        Restore the default configuration. Backup the current config before restoring.
        """
        backup_path = ConfigManager.CONFIG_FILE_PATH + ".backup"
        try:
            # Backup current config
            if os.path.exists(ConfigManager.CONFIG_FILE_PATH):
                shutil.copy2(ConfigManager.CONFIG_FILE_PATH, backup_path)
            current_setup_complete = ConfigManager().get_config("SETUP_COMPLETE")

            # Write default config
            conf = {key: value for key, value in ConfigManager.DEFAULT_CONFIG.items()}
            conf["SETUP_COMPLETE"] = current_setup_complete
            with open(ConfigManager.CONFIG_FILE_PATH, "w") as f:
                json.dump(conf, indent=2, fp=f)
            logger.info("Default configuration restored.")

            # Remove backup if successful
            if os.path.exists(backup_path):
                os.remove(backup_path)
            return True
        except Exception as e:
            logger.error(f"Error restoring default configuration: {str(e)}")
            if os.path.exists(backup_path):
                # Restore backup if it exists
                shutil.copy2(backup_path, ConfigManager.CONFIG_FILE_PATH)
                os.remove(backup_path)
                logger.info("Previous configuration restored from backup.")
            return False
