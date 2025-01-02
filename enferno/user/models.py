import json
from typing import Any, Dict
from datetime import datetime
from uuid import uuid4

from flask import current_app, session
from flask_security import UserMixin, RoleMixin
from flask_security import current_user
from flask_security.utils import hash_password
from sqlalchemy import JSON, ARRAY
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.mutable import Mutable

from enferno.extensions import db, rds
from enferno.settings import Config as cfg
from enferno.utils.base import BaseMixin
from enferno.utils.logging_utils import get_logger

# Redis key namespace to set flag for forcing password reset
SECURITY_KEY_NAMESPACE = "security:user"

logger = get_logger()


class MutableList(Mutable, list):
    """Custom Mutable List class to track changes in the list."""

    def append(self, value: Any) -> None:
        """
        Append a value to the list and mark the list as changed.

        Args:
            - value: The value to append to the list.

        Returns:
            None
        """
        list.append(self, value)
        self.changed()

    def pop(self, index: int = 0) -> Any:
        """
        Pop a value from the list and mark the list as changed.

        Args:
            - index: The index of the value to pop.

        Returns:
            - The value that was popped from the list.
        """
        value = list.pop(self, index)
        self.changed()
        return value

    @classmethod
    def coerce(cls, key: Any, value: Any) -> Any:
        """
        Coerce a value into a Mutable List.

        Args:
            - key: The key of the value.
            - value: The value to coerce.

        Returns:
            - The coerced value as a Mutable List.
        """
        if not isinstance(value, MutableList):
            if isinstance(value, list):
                return MutableList(value)
            return Mutable.coerce(key, value)
        else:
            return value


roles_users = db.Table(
    "roles_users",
    db.Column("user_id", db.Integer(), db.ForeignKey("user.id")),
    db.Column("role_id", db.Integer(), db.ForeignKey("role.id")),
)


class Role(db.Model, RoleMixin, BaseMixin):
    """Role model"""

    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    color = db.Column(db.String(10))
    description = db.Column(db.String(255))

    # Permissions List

    # ---- General -------
    view_simple_history = db.Column(db.Boolean, default=True)

    # ---- Bulletin -------
    view_bulletin = db.Column(db.Boolean, default=True)
    edit_bulletin = db.Column(db.Boolean, default=True)
    delete_bulletin = db.Column(db.Boolean, default=True)

    settings = db.Column(JSON)

    def to_dict(self) -> dict:
        """Return a dictionary representation of the Role object."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color": self.color or "",
        }

    def to_json(self) -> str:
        """Return a JSON representation of the Role object."""
        return json.dumps(self.to_dict())

    def from_json(self, jsn: dict) -> "Role":
        """
        Populate the Role object from a JSON dictionary.

        Args:
            - jsn: The JSON dictionary to populate the Role object from.

        Returns:
            - The Role object.
        """
        self.name = jsn.get("name")
        self.description = jsn.get("description", "")
        self.color = jsn.get("color")
        return self

    def __repr__(self):
        return "{} - {}".format(self.id, self.name)


class WebAuthn(db.Model):
    """WebAuthn model for user authentication"""

    id = db.Column(db.Integer, primary_key=True)
    credential_id = db.Column(db.LargeBinary(1024), index=True, nullable=False, unique=True)
    public_key = db.Column(db.LargeBinary(1024), nullable=False)
    sign_count = db.Column(db.Integer, default=0, nullable=False)
    transports = db.Column(MutableList.as_mutable(ARRAY(db.String)), nullable=True)
    extensions = db.Column(db.String(255))
    lastuse_datetime = db.Column(db.DateTime, nullable=False)
    name = db.Column(db.String(64), nullable=False)
    usage = db.Column(db.String(64), nullable=False)
    backup_state = db.Column(db.Boolean, nullable=False)
    device_type = db.Column(db.String(64), nullable=False)

    @declared_attr
    def user_id(cls):
        return db.Column(
            db.Integer,
            db.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        )

    def get_user_mapping(self) -> dict:
        """
        Return the mapping from webauthn back to User.
        """
        return dict(id=self.user_id)


class User(UserMixin, db.Model, BaseMixin):
    """User model"""

    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False, default=uuid4().hex)
    name = db.Column(db.String(255))
    picture = db.Column(db.String(255))
    email = db.Column(db.String(255), nullable=True)
    username = db.Column(db.String(255), nullable=True, unique=True)
    password = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=False)
    roles = db.relationship(
        "Role", secondary=roles_users, backref=db.backref("users", lazy="dynamic")
    )

    # email confirmation
    confirmed_at = db.Column(db.DateTime())
    # tracking
    last_login_at = db.Column(db.DateTime())
    current_login_at = db.Column(db.DateTime())
    last_login_ip = db.Column(db.String(255))
    current_login_ip = db.Column(db.String(255))
    login_count = db.Column(db.Integer())

    # web authn
    fs_webauthn_user_handle = db.Column(db.String(64), unique=True)

    tf_phone_number = db.Column(db.String(64))
    tf_primary_method = db.Column(db.String(140))
    tf_totp_secret = db.Column(db.String(255))

    mf_recovery_codes = db.Column(MutableList.as_mutable(ARRAY(db.String)), nullable=True)

    # individual abilities
    view_usernames = db.Column(db.Boolean, default=True)
    view_simple_history = db.Column(db.Boolean, default=True)
    view_full_history = db.Column(db.Boolean, default=True)
    can_self_assign = db.Column(db.Boolean, default=False)
    can_edit_locations = db.Column(db.Boolean, default=False)
    can_export = db.Column(db.Boolean, default=False)
    can_import_web = db.Column(db.Boolean, default=False)

    # oauth
    google_id = db.Column(db.String(255))

    settings = db.Column(JSON)

    @declared_attr
    def webauthn(cls):
        return db.relationship("WebAuthn", backref="users", cascade="all, delete")

    @property
    def security_reset_key(self):
        """Get the timestamp value from Redis"""
        value = rds.get(f"{SECURITY_KEY_NAMESPACE}:{self.id}")
        return value.decode() if value else None

    def set_security_reset_key(self) -> None:
        """Set the security reset key with a timestamp value"""
        key = f"{SECURITY_KEY_NAMESPACE}:{self.id}"
        timestamp = int(datetime.utcnow().timestamp())
        rds.set(key, timestamp)

    def unset_security_reset_key(self) -> None:
        """unSet the security reset key"""
        key = f"{SECURITY_KEY_NAMESPACE}:{self.id}"
        rds.delete(key)

    def roles_in(self, roles: list) -> bool:
        chk = [self.has_role(r) for r in roles]
        return any(chk)

    def __unicode__(self):
        return "%s" % self.id

    def __repr__(self):
        return "%s %s %s" % (self.name, self.id, self.email)

    def logout_other_sessions(self):
        rds = current_app.config["SESSION_REDIS"]
        current_session_id = session.sid
        errors = []

        for s in self.sessions:
            if s.session_token == current_session_id:
                continue  # Skip current session
            try:
                session_key = f"session:{s.session_token}"
                if rds.exists(session_key):
                    rds.delete(session_key)
            except Exception as e:
                errors.append(f"Failed to delete session {s.session_token}: {str(e)}")
        if errors:
            logger.error("Failed to delete some sessions: %s", errors)

    @property
    def secure_email(self):
        try:
            if (
                current_user.view_usernames
                or current_user.has_role("Admin")
                or current_user is None
            ):
                return self.email
        except Exception as ex:
            pass
        return f"user-{self.id}"

    @property
    def secure_name(self):
        try:
            if (
                current_user.view_usernames
                or current_user.has_role("Admin")
                or current_user is None
            ):
                return self.name
        except Exception as ex:
            pass
        return f"user-{self.id}"

    @property
    def secure_username(self):
        try:
            if (
                current_user.view_usernames
                or current_user.has_role("Admin")
                or current_user is None
            ):
                return self.username
        except Exception as ex:
            pass
        return f"user-{self.id}"

    def can_access(self, obj: Any) -> bool:
        """
        check if user can access a specific entity.

        Args:
            - obj: The entity to check access for. Bulletin, Actor, Incident, etc.

        Returns:
            - bool: True if the user can access the entity, False otherwise.
        """
        # grant admin access always to restricted items
        if self.has_role("Admin"):
            return True

        # handle primary entities (bulletins, actors, incidents)
        if obj.__tablename__ in ["bulletin", "actor", "incident"]:
            # intersect roles
            if set(self.roles) & set(obj.roles):
                return True

            if not cfg.ACCESS_CONTROL_RESTRICTIVE and not obj.roles:
                return True

        # handle media access
        elif obj.__tablename__ == "media":
            # media can be related to either an actor or a bulletin
            # find out which one
            parent = obj.bulletin or obj.actor
            # Restrict all medias without a parent
            # intersect roles with parent
            if parent:
                if set(self.roles) & set(parent.roles):
                    return True
                if not cfg.ACCESS_CONTROL_RESTRICTIVE and not parent.roles:
                    return True

        return False

    def from_json(self, item: dict) -> "User":
        """
        Populate the User object from a JSON dictionary.

        Args:
            - item: The JSON dictionary to populate the User object from.

        Returns:
            - The User object.
        """
        self.email = item.get("email")
        self.username = item.get("username")

        # check password is not empty
        password = item.get("password")
        if password:
            self.password = hash_password(password)

        self.name = item.get("name")

        # roles
        roles = item.get("roles", [])
        new_roles = []
        if len(roles):
            ids = [r.get("id", -1) for r in roles]
            new_roles = Role.query.filter(Role.id.in_(ids)).all()
            self.roles = new_roles
        else:
            self.roles = []

        # permissions
        self.view_usernames = item.get("view_usernames", False)
        self.view_simple_history = item.get("view_simple_history", False)
        self.view_full_history = item.get("view_full_history", False)
        self.can_self_assign = item.get("can_self_assign", False)
        self.can_edit_locations = item.get("can_edit_locations", False)
        self.can_export = item.get("can_export", False)
        self.can_import_web = item.get("can_import_web", False)
        self.active = item.get("active")
        return self

    @property
    def two_factor_devices(self) -> Dict[str, Any]:
        """
        Unified list of user's 2FA methods and devices.

        Returns a list of dictionaries, each representing a 2FA method or device.
        Combines traditional 2FA methods (authenticator, phone) with WebAuthn devices,
        providing a consistent structure for easy display and management.

        Returns:
            list: A list of dictionaries containing 2FA device information.
        """
        devices = []

        # Add primary 2FA method if set
        if self.tf_primary_method:
            if self.tf_primary_method == "authenticator":
                devices.append(
                    {"type": "authenticator", "name": "Authenticator App", "is_primary": True}
                )

        # Add WebAuthn devices
        for device in self.webauthn:
            devices.append(
                {
                    "type": "webauthn",
                    "name": device.name,
                    "last_used": device.lastuse_datetime.isoformat(),
                    "device_type": device.device_type,
                    "is_primary": device.usage == "primary",
                    "backup_state": device.backup_state,
                }
            )

        return devices

    def to_compact(self) -> dict:
        """
        Compact serializer for User class.
        Hides user data from users without
        permissions.
        """
        return {
            "id": self.id,
            "name": self.secure_name,
            "username": self.secure_username,
            "active": self.active,
        }

    def to_dict(self) -> dict:
        """
        Main serializer for User class.
        """
        return {
            "id": self.id,
            "name": self.secure_name,
            "google_id": self.google_id,
            "email": self.secure_email,
            "username": self.secure_username,
            "active": self.active,
            "roles": [role.to_dict() for role in self.roles],
            "view_usernames": self.view_usernames,
            "view_simple_history": self.view_simple_history,
            "view_full_history": self.view_full_history,
            "can_self_assign": self.can_self_assign,
            "can_edit_locations": self.can_edit_locations,
            "can_export": self.can_export,
            "can_import_web": self.can_import_web,
            "force_reset": self.security_reset_key,
            "two_factor_devices": self.two_factor_devices,
        }

    def to_json(self) -> str:
        """Return a JSON representation of the User object."""
        return json.dumps(self.to_dict())

    meta = {
        "allow_inheritance": True,
        "indexes": ["-created_at", "email", "username"],
        "ordering": ["-created_at"],
    }


class Session(db.Model, BaseMixin):
    __tablename__ = "sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", backref=db.backref("sessions", lazy=True))

    session_token = db.Column(db.String(255), unique=True, nullable=False)
    last_active = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)
    ip_address = db.Column(db.String(255))

    # Combined metadata field for location, browser, and operating system details
    meta = db.Column(JSON)

    is_active = db.Column(db.Boolean, default=True)  # To track if the session is currently active

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "last_active": self.last_active,
            "expires_at": self.expires_at,
            "ip_address": self.ip_address,
            "meta": self.meta,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
