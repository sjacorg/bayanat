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

    # Singleton state
    _instance = None
    _config = {}
    _mtime = 0
    _last_check = 0

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
    # Only these two are genuinely cached at init time.
    # All SECURITY_* keys are read live per-request by Flask-Security via config_value().
    STATIC_KEYS = frozenset(
        {
            "RECAPTCHA_ENABLED",  # login form class chosen at Security() init
            "GOOGLE_OAUTH_ENABLED",  # CSP rules set at Talisman init
        }
    )

    # Type conversions from raw JSON values to Python types
    TYPE_CONVERSIONS = {
        "SECURITY_FRESHNESS": lambda v: timedelta(minutes=v),
        "SECURITY_FRESHNESS_GRACE_PERIOD": lambda v: timedelta(minutes=v),
        "ACTIVITIES_RETENTION": lambda v: timedelta(days=max(90, int(v))),
        "EXPORT_DEFAULT_EXPIRY": lambda v: timedelta(hours=v),
        "MAIL_PORT": int,
    }

    # All keys in DEFAULT_CONFIG minus STATIC_KEYS are dynamic
    DYNAMIC_KEYS = frozenset(set(DEFAULT_CONFIG.keys()) - STATIC_KEYS) | frozenset(
        {
            "GEO_MAP_DEFAULT_CENTER_LAT",
            "GEO_MAP_DEFAULT_CENTER_LNG",
            "GEO_MAP_DEFAULT_CENTER_RADIUS",
            "ACTIVITIES_LIST",
        }
    )

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        try:
            with open(self.CONFIG_FILE_PATH) as file:
                self._config = json.loads(file.read())
            self._mtime = os.path.getmtime(self.CONFIG_FILE_PATH)
        except EnvironmentError:
            logger.error("No config file found, Loading default Bayanat configurations")
            self._config = {}
            self._mtime = 0
        self._last_check = time.time()
        # Keep instance-level config for backward compat with settings.py
        self.config = self._config

    def get(self, key, default=None):
        """Get a config value with auto-reload, type conversion, and derived key support."""
        self._maybe_reload()

        # Derived keys
        if key == "GEO_MAP_DEFAULT_CENTER_LAT":
            geo = self._get_raw("GEO_MAP_DEFAULT_CENTER")
            return geo.get("lat") if geo else default
        if key == "GEO_MAP_DEFAULT_CENTER_LNG":
            geo = self._get_raw("GEO_MAP_DEFAULT_CENTER")
            return geo.get("lng") if geo else default
        if key == "GEO_MAP_DEFAULT_CENTER_RADIUS":
            geo = self._get_raw("GEO_MAP_DEFAULT_CENTER")
            return geo.get("radius", 1000) if geo else default
        if key == "ACTIVITIES_LIST":
            activities = self._get_raw("ACTIVITIES")
            if activities:
                return [k for k, v in activities.items() if v]
            return default

        raw = self._get_raw(key)
        if raw is None:
            return default

        converter = self.TYPE_CONVERSIONS.get(key)
        return converter(raw) if converter else raw

    def _get_raw(self, key):
        """Get raw value from config with DEFAULT_CONFIG fallback."""
        value = self._config.get(key)
        if value is not None:
            return value
        return self.DEFAULT_CONFIG.get(key)

    def _maybe_reload(self):
        now = time.time()
        if now - self._last_check < self.CHECK_INTERVAL:
            return
        self._last_check = now
        try:
            mtime = os.path.getmtime(self.CONFIG_FILE_PATH)
            if mtime != self._mtime:
                self._load()
        except OSError:
            pass

    def _load(self):
        try:
            with open(self.CONFIG_FILE_PATH) as f:
                new_config = json.loads(f.read())
            # Atomic reference swap - thread-safe under GIL
            self._config = new_config
            self.config = new_config
            self._mtime = os.path.getmtime(self.CONFIG_FILE_PATH)
            logger.info("Configuration reloaded from file.")
        except Exception:
            logger.error("Failed to reload config", exc_info=True)

    def force_reload(self):
        """Force immediate reload of config from file."""
        self._load()
        self._last_check = time.time()

    # Backward-compatible method used by settings.py at import time
    def get_config(self, cfg):
        value = self.config.get(cfg)
        if value is not None:
            return value
        else:
            return ConfigManager.DEFAULT_CONFIG.get(cfg)

    @staticmethod
    def detect_static_changes(app):
        """Compare current app.config static keys against what's now in config.json.
        Returns set of static keys that changed."""
        cm = ConfigManager.instance()
        changed = set()
        for key in ConfigManager.STATIC_KEYS:
            new_raw = cm._get_raw(key)
            converter = ConfigManager.TYPE_CONVERSIONS.get(key)
            new_val = converter(new_raw) if converter and new_raw is not None else new_raw
            # Read from the underlying dict (not through DynamicConfig proxy)
            old_val = dict.get(app.config, key)
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
        Reads from ConfigManager singleton for live values."""
        cm = ConfigManager.instance()

        # Secret fields that need masking
        from enferno.admin.models import AppConfig

        conf = {}
        for key in ConfigManager.DEFAULT_CONFIG:
            raw = cm._get_raw(key)
            if raw is None:
                raw = ConfigManager.DEFAULT_CONFIG.get(key)

            # Apply type conversions for serialization (reverse them for display)
            if key in ("SECURITY_FRESHNESS", "SECURITY_FRESHNESS_GRACE_PERIOD"):
                # Store as minutes in JSON
                conf[key] = raw
            elif key == "ACTIVITIES_RETENTION":
                # Store as days in JSON
                conf[key] = raw
            elif key == "EXPORT_DEFAULT_EXPIRY":
                # Store as hours in JSON
                conf[key] = raw
            elif key == "MAIL_PORT":
                conf[key] = int(raw) if raw is not None else 25
            elif key in AppConfig.SECRET_FIELDS:
                conf[key] = ConfigManager.MASK_STRING if raw else ""
            else:
                conf[key] = raw

        # GEO_MAP_DEFAULT_CENTER is stored as nested dict in config.json, serialize as-is
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
                conf[secret_field] = cm._get_raw(secret_field) or ""

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


class DynamicConfig(dict):
    """Flask config dict that reads dynamic keys live from ConfigManager.

    Static keys and Flask internals are served from the underlying dict.
    Dynamic app config keys are proxied through ConfigManager for live reload.

    Supports patch.dict() in tests by tracking explicit overrides via
    __setitem__/update that differ from what ConfigManager returns.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._overrides = set()
        self._init_done = True

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if not getattr(self, "_init_done", False):
            return
        if key in ConfigManager.DYNAMIC_KEYS:
            cm_val = ConfigManager.instance().get(key)
            if value != cm_val:
                self._overrides.add(key)
            else:
                self._overrides.discard(key)

    def __delitem__(self, key):
        super().__delitem__(key)
        self._overrides.discard(key)

    def update(self, __m=None, **kwargs):
        if __m:
            items = __m.items() if hasattr(__m, "items") else __m
            for k, v in items:
                self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def __getitem__(self, key):
        if key in ConfigManager.DYNAMIC_KEYS and key not in self._overrides:
            val = ConfigManager.instance().get(key)
            if val is not None:
                return val
        return super().__getitem__(key)

    def get(self, key, default=None):
        if key in ConfigManager.DYNAMIC_KEYS and key not in self._overrides:
            val = ConfigManager.instance().get(key)
            return val if val is not None else default
        return super().get(key, default)

    def __contains__(self, key):
        if key in ConfigManager.DYNAMIC_KEYS:
            return True
        return super().__contains__(key)
