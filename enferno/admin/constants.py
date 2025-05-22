from enum import Enum


class Constants:
    CLASSIC_OPTS = ["Yes", "No", "Unknown"]
    PHYSIQUE_OPTS = ["Very Thin", "Thin", "Average", "Muscular", "Overweight", "Obese"]
    HAIR_LOSS_OPTS = ["Full", "Bald", "Partial hair loss"]
    HAIR_TYPE_OPTS = ["Straight", "Wavy", "Curly", "Very curly"]
    HAIR_LENGTH_OPTS = ["Very short", "Short", "Medium", "Long", "Very long"]
    HAIR_COLOR_OPTS = ["Black", "Brown", "Blonde", "Red", "Grey", "Turning grey", "Red", "Other"]
    FACIAL_HAIR_OPTS = ["None", "Beard", "Moustache", "Beard and moustache", "Goatee", "Whiskers"]
    HANDEDNESS_OPTS = ["Right", "Left", "Both Hands", "Unknown"]
    CASE_STATUS_OPTS = ["Missing", "Identified"]
    SMOKER_OPTS = ["Yes", "No", "Unknown", "Question Not Asked"]
    SKIN_MARKINGS_OPTS = ["Scar", "Tattoo", "piercing", "Mole", "Birthmarks", "Cuts"]
    PREGNANT_AT_DISAPPEARANCE_OPTS = [
        "Pregnant",
        "Not Pregnant",
        "Unknown",
        "Not Applicable",
        "The Question Was Not Asked",
    ]
    WHISPER_MODEL_OPTS = [
        {"model_name": "tiny", "model_label": "Tiny", "param_size": 39_000_000, "est_vram": "1 GB"},
        {
            "model_name": "tiny.en",
            "model_label": "Tiny (English only)",
            "param_size": 39_000_000,
            "est_vram": "1 GB",
        },
        {"model_name": "base", "model_label": "Base", "param_size": 74_000_000, "est_vram": "1 GB"},
        {
            "model_name": "base.en",
            "model_label": "Base (English only)",
            "param_size": 74_000_000,
            "est_vram": "1 GB",
        },
        {
            "model_name": "small",
            "model_label": "Small",
            "param_size": 244_000_000,
            "est_vram": "2 GB",
        },
        {
            "model_name": "small.en",
            "model_label": "Small (English only)",
            "param_size": 244_000_000,
            "est_vram": "2 GB",
        },
        {
            "model_name": "medium",
            "model_label": "Medium",
            "param_size": 769_000_000,
            "est_vram": "5 GB",
        },
        {
            "model_name": "medium.en",
            "model_label": "Medium (English only)",
            "param_size": 769_000_000,
            "est_vram": "5 GB",
        },
        {
            "model_name": "large",
            "model_label": "Large",
            "param_size": 1_550_000_000,
            "est_vram": "10 GB",
        },
        {
            "model_name": "turbo",
            "model_label": "Turbo",
            "param_size": 809_000_000,
            "est_vram": "6 GB",
        },
    ]

    class NotificationEvent(Enum):
        """
        Notification events that are used in the app.
        """

        LOGIN_NEW_IP = "LOGIN_NEW_IP"
        PASSWORD_CHANGE = "PASSWORD_CHANGE"
        TWO_FACTOR_CHANGE = "TWO_FACTOR_CHANGE"
        RECOVERY_CODES_CHANGE = "RECOVERY_CODES_CHANGE"
        FORCE_PASSWORD_CHANGE = "FORCE_PASSWORD_CHANGE"
        NEW_USER = "NEW_USER"
        UPDATE_USER = "UPDATE_USER"
        NEW_GROUP = "NEW_GROUP"
        SYSTEM_SETTINGS_CHANGE = "SYSTEM_SETTINGS_CHANGE"
        LOGIN_NEW_COUNTRY = "LOGIN_NEW_COUNTRY"
        UNAUTHORIZED_ACTION = "UNAUTHORIZED_ACTION"
        ADMIN_CREDENTIALS_CHANGE = "ADMIN_CREDENTIALS_CHANGE"
        ITEM_DELETED = "ITEM_DELETED"
        NEW_EXPORT = "NEW_EXPORT"
        EXPORT_APPROVED = "EXPORT_APPROVED"
        NEW_BATCH = "NEW_BATCH"
        BATCH_STATUS = "BATCH_STATUS"
        BULK_OPERATION_STATUS = "BULK_OPERATION_STATUS"
        WEB_IMPORT_STATUS = "WEB_IMPORT_STATUS"
        NEW_ASSIGNMENT = "NEW_ASSIGNMENT"
        REVIEW_NEEDED = "REVIEW_NEEDED"
