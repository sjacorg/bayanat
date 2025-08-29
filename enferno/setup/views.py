from typing import Optional, Dict, Any

from flask import (
    request,
    redirect,
    Blueprint,
    send_from_directory,
    render_template,
    Response,
    current_app,
)
from flask_security import hash_password, login_user, roles_required, current_user

from enferno.admin.models import Eventtype, PotentialViolation, ClaimedViolation
from enferno.extensions import db
from enferno.user.models import User, Role
from enferno.utils.config_utils import ConfigManager
from enferno.utils.data_helpers import import_default_data
from enferno.utils.http_response import HTTPResponse

from enferno.admin.validation.models import WizardConfigRequestModel
from enferno.utils.validation_utils import validate_with

bp_setup = Blueprint("setup", __name__, static_folder="../static")


def check_installation() -> bool:
    """Check if the application is installed."""
    return not current_app.config.get("SETUP_COMPLETE", False)


@bp_setup.before_app_request
def handle_installation_check() -> Optional[Response]:
    """Redirect to setup wizard if the app is not installed."""
    excluded_paths = [
        "/setup_wizard",
        "/static",
        "/assets",
        "/_debug_toolbar",
        "/favicon.ico",
        "/api/create-admin",
        "/api/check-admin",
        "/api/default-config",
        "/api/import-data",
        "/api/check-data-imported",
        "/admin/api/configuration/",
        "/admin/api/location-admin-levels/",
        "/admin/api/location-admin-level",
        "/api/complete-setup",
        "/admin/api/reload",
        "/fs-static",
    ]
    login_flow_paths = [
        "/login",
        "/wan-signin",
        "/tf-validate",
        "/tf-select",
    ]

    # Add /login to excluded paths if users exist
    if User.query.first() is not None:
        excluded_paths.extend(login_flow_paths)

    if not any(request.path.startswith(path) for path in excluded_paths):
        if check_installation():
            return redirect("/setup_wizard")


@bp_setup.route("/setup_wizard")
def setup_wizard() -> str:
    """Render the setup wizard template."""
    return render_template("setup_wizard.html")


@bp_setup.post("/api/create-admin")
def create_admin() -> Any:
    """Create an admin user if one doesn't exist."""
    admin_role = Role.query.filter(Role.name == "Admin").first()

    if admin_role.users.all():
        return HTTPResponse.error("Admin user already exists")

    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return HTTPResponse.error("Username and password are required")

    if User.query.filter(User.username == username.lower()).first():
        return HTTPResponse.error("Username already exists")

    new_admin = User(username=username, password=hash_password(password), active=1, name="Admin")
    new_admin.roles.append(admin_role)

    db.session.add(new_admin)
    try:
        db.session.commit()
        login_user(new_admin)
        return HTTPResponse.created(
            message="Admin user installed successfully",
            data={"item": new_admin.to_dict()},
        )
    except Exception as e:
        db.session.rollback()
        return HTTPResponse.error("Failed to create admin user", status=500)


@bp_setup.get("/api/check-admin")
def check_admin() -> Dict[str, str]:
    """Check if an admin user exists."""
    admin_role = Role.query.filter(Role.name == "Admin").first()
    if admin_role and admin_role.users.first():
        return HTTPResponse.success(data={"status": "exists"}, message="Admin user already exists")
    else:
        return HTTPResponse.success(data={"status": "not_found"}, message="No admin user found")


@bp_setup.post("/api/import-data")
@roles_required("Admin")
def import_data() -> Response:
    """Import default data into the database."""
    try:
        import_default_data()
        return HTTPResponse.success(message="Default data imported successfully")
    except Exception as e:
        return HTTPResponse.error("Failed to import default data", status=500)


@bp_setup.get("/api/check-data-imported")
def check_data_imported() -> Dict[str, str]:
    """Check if default data has been imported."""
    if User.query.first() is not None:
        if not current_user.has_role("Admin"):
            return HTTPResponse.forbidden()

    data_exists = (
        Eventtype.query.first() is not None
        and PotentialViolation.query.first() is not None
        and ClaimedViolation.query.first() is not None
    )
    if data_exists:
        return HTTPResponse.success(
            data={"status": "imported"}, message="Default data has been imported"
        )
    else:
        return HTTPResponse.success(
            data={"status": "not_imported"},
            message="Default data has not been imported",
        )


@bp_setup.get("/api/default-config")
def get_default_config() -> Dict[str, Any]:
    """Retrieve the default configuration for specific keys."""
    if User.query.first() is not None:
        if not current_user.has_role("Admin"):
            return HTTPResponse.forbidden()

    required_keys = [
        "FILESYSTEM_LOCAL",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "S3_BUCKET",
        "AWS_REGION",
        "BABEL_DEFAULT_LOCALE",
        "ACCESS_CONTROL_RESTRICTIVE",
        "AC_USERS_CAN_RESTRICT_NEW",
        "ACTIVITIES_RETENTION",
        "EXPORT_DEFAULT_EXPIRY",
        "SESSION_RETENTION_PERIOD",
        "ETL_TOOL",
        "SHEET_IMPORT",
        "WEB_IMPORT",
        "EXPORT_TOOL",
        "GOOGLE_MAPS_API_KEY",
        "GEO_MAP_DEFAULT_CENTER",
        "SECURITY_TWO_FACTOR_REQUIRED",
        "SECURITY_PASSWORD_LENGTH_MIN",
        "SECURITY_ZXCVBN_MINIMUM_SCORE",
        "SESSION_RETENTION_PERIOD",
    ]

    default_config = ConfigManager.DEFAULT_CONFIG
    filtered_config = {key: default_config[key] for key in required_keys if key in default_config}
    return HTTPResponse.success(
        data=filtered_config, message="Default configuration retrieved successfully"
    )


@bp_setup.put("/api/complete-setup/")
@validate_with(WizardConfigRequestModel)
@roles_required("Admin")
def api_config_write(
    validated_data: dict,
) -> Response:
    """
    Writes app configuration and completes setup.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    conf = validated_data.get("conf")

    conf["SETUP_COMPLETE"] = True

    if ConfigManager.write_config(conf):
        return HTTPResponse.success(message="Configuration Saved Successfully")
    else:
        return HTTPResponse.error("Unable to Save Configuration", status=417)
