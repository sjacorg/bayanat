import json
import time
from datetime import timedelta
from types import MappingProxyType
from flask_security import current_user

import logging
import os
import shutil
from enferno.admin.constants import Constants
from enferno.utils.notification_config import NOTIFICATIONS_DEFAULT_CONFIG

NotificationEvent = Constants.NotificationEvent

logger = logging.getLogger("app_logger")


class ConfigManager:
    CONFIG_FILE_PATH = os.environ.get("BAYANAT_CONFIG_FILE", "config.json")
    MASK_STRING = "**********"
    CHECK_INTERVAL = 5  # seconds between mtime checks

    _instance = None

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
            "NOTIFICATIONS": NOTIFICATIONS_DEFAULT_CONFIG,  # Import from notification_config.py
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
            "GOOGLE_CLIENT_ID": "Google Client ID",
            "GOOGLE_CLIENT_SECRET": "Google Client Secret",
            "GOOGLE_DISCOVERY_URL": "Google Discovery URL",
            "FILESYSTEM_LOCAL": "Filesystem Local",
            "AWS_ACCESS_KEY_ID": "AWS Access Key ID",
            "AWS_SECRET_ACCESS_KEY": "AWS Secret Access Key",
            "S3_BUCKET": "S3 Bucket",
            "AWS_REGION": "AWS Region",
            "ACCESS_CONTROL_RESTRICTIVE": "Restrictive Access Control",
            "AC_USERS_CAN_RESTRICT_NEW": "Users Can Restrict New Items",
            "MEDIA_ALLOWED_EXTENSIONS": "Media Upload Allowed File Extensions",
            "MEDIA_UPLOAD_MAX_FILE_SIZE": "Media Maximum File Upload Size",
            "SHEETS_ALLOWED_EXTENSIONS": "Sheets Allowed File Extensions",
            "ETL_TOOL": "ETL Tool",
            "ETL_PATH_IMPORT": "Media Import from a local path",
            "ETL_VID_EXT": "Media Import Allowed File Extensions",
            "OCR_ENABLED": "OCR Enabled",
            "OCR_EXT": "OCR Allowed File Extensions",
            "SHEET_IMPORT": "Sheet Import",
            "DEDUP_TOOL": "Dedup Tool",
            "BABEL_DEFAULT_LOCALE": "Default System Language",
            "MAPS_API_ENDPOINT": "Google Maps API Endpoint",
            "GOOGLE_MAPS_API_KEY": "Google Maps API Key",
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
            "ACTIVITIES": "Activity Monitor",
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
            "NOTIFICATIONS": "Notifications",
        }
    )

    # Keys that require process restart (form classes / CSP registered at init)
    STATIC_KEYS = frozenset(
        {
            "RECAPTCHA_ENABLED",  # login form class chosen at Security() init
            "GOOGLE_OAUTH_ENABLED",  # CSP rules set at Talisman init
            "MAIL_SERVER",  # Flask-Mail caches connection settings at init
            "MAIL_PORT",
            "MAIL_USE_TLS",
            "MAIL_USE_SSL",
            "MAIL_USERNAME",
            "MAIL_PASSWORD",
            "MAIL_DEFAULT_SENDER",
            "DEDUP_TOOL",  # Celery beat tasks registered once at startup
            "DEDUP_INTERVAL",
        }
    )

    # Type conversions from raw JSON values to Python types expected by Flask
    TYPE_CONVERSIONS = {
        "SECURITY_FRESHNESS": lambda v: timedelta(minutes=v),
        "SECURITY_FRESHNESS_GRACE_PERIOD": lambda v: timedelta(minutes=v),
        "ACTIVITIES_RETENTION": lambda v: timedelta(days=max(90, int(v))),
        "EXPORT_DEFAULT_EXPIRY": lambda v: timedelta(hours=v),
        "MAIL_PORT": int,
    }

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._mtime = 0
        self._last_check = 0
        try:
            with open(self.CONFIG_FILE_PATH) as file:
                self.config = json.loads(file.read())
            self._mtime = os.path.getmtime(self.CONFIG_FILE_PATH)
        except EnvironmentError:
            logger.error("No config file found, Loading default Bayanat configurations")
            self.config = {}
        self._last_check = time.time()

    def get_config(self, cfg):
        """Get raw config value with DEFAULT_CONFIG fallback."""
        value = self.config.get(cfg)
        if value is not None:
            return value
        return ConfigManager.DEFAULT_CONFIG.get(cfg)

    def force_reload(self):
        """Force immediate reload of config from file."""
        try:
            with open(self.CONFIG_FILE_PATH) as f:
                self.config = json.loads(f.read())
            self._mtime = os.path.getmtime(self.CONFIG_FILE_PATH)
            self._last_check = time.time()
            logger.info("Configuration reloaded from file.")
        except Exception:
            logger.error("Failed to reload config", exc_info=True)

    def maybe_reload(self):
        """Check file mtime and reload if changed. Used by Celery workers."""
        now = time.time()
        if now - self._last_check < self.CHECK_INTERVAL:
            return
        self._last_check = now
        try:
            mtime = os.path.getmtime(self.CONFIG_FILE_PATH)
            if mtime != self._mtime:
                self.force_reload()
        except OSError:
            pass

    @staticmethod
    def apply_to_app(app):
        """Update app.config dict in-place from config.json values.

        Applies type conversions and derived keys. Skips STATIC_KEYS
        since those require a process restart to take effect.
        """
        cm = ConfigManager.instance()
        for key in ConfigManager.DEFAULT_CONFIG:
            if key in ConfigManager.STATIC_KEYS:
                continue
            raw = cm.get_config(key)
            converter = ConfigManager.TYPE_CONVERSIONS.get(key)
            app.config[key] = converter(raw) if converter and raw is not None else raw

        # Derived keys
        geo = cm.get_config("GEO_MAP_DEFAULT_CENTER")
        if geo:
            app.config["GEO_MAP_DEFAULT_CENTER_LAT"] = geo.get("lat")
            app.config["GEO_MAP_DEFAULT_CENTER_LNG"] = geo.get("lng")
            app.config["GEO_MAP_DEFAULT_CENTER_RADIUS"] = geo.get("radius", 1000)

        activities = cm.get_config("ACTIVITIES")
        if activities:
            app.config["ACTIVITIES_LIST"] = [k for k, v in activities.items() if v]

    @staticmethod
    def detect_static_changes(app):
        """Return set of STATIC_KEYS whose values differ from config.json."""
        cm = ConfigManager.instance()
        changed = set()
        for key in ConfigManager.STATIC_KEYS:
            new_val = cm.get_config(key)
            old_val = app.config.get(key)
            if old_val != new_val:
                changed.add(key)
        return changed

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
        """Serialize current config for the admin UI.
        Returns raw JSON values (no type conversions) with secrets masked."""
        from enferno.admin.models import AppConfig

        cm = ConfigManager.instance()
        conf = {}
        for key in ConfigManager.DEFAULT_CONFIG:
            raw = cm.get_config(key)
            if key in AppConfig.SECRET_FIELDS:
                conf[key] = ConfigManager.MASK_STRING if raw else ""
            elif key == "MAIL_PORT":
                conf[key] = int(raw) if raw is not None else 25
            else:
                conf[key] = raw
        return conf

    @staticmethod
    def validate(conf):
        return True

    @staticmethod
    def write_config(conf):
        from enferno.admin.models import AppConfig, Activity

        # Handle masked secrets - restore from current config
        cm = ConfigManager.instance()
        for secret_field in AppConfig.SECRET_FIELDS:
            if conf.get(secret_field) == ConfigManager.MASK_STRING:
                conf[secret_field] = cm.get_config(secret_field) or ""

        if ConfigManager.validate(conf):
            try:
                # Create sanitized config without secrets
                sanitized_conf = {
                    key: value for key, value in conf.items() if key not in AppConfig.SECRET_FIELDS
                }

                app_config = AppConfig()
                app_config.config = sanitized_conf
                app_config.user_id = current_user.id
                app_config.save()

                Activity.create(
                    current_user,
                    Activity.ACTION_CREATE,
                    Activity.STATUS_SUCCESS,
                    app_config.to_mini(),
                    "config",
                )

                # Write full config (including secrets) to file system
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
