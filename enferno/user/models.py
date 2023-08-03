import json
from uuid import uuid4

from flask_security import UserMixin, RoleMixin
from flask_security import current_user
from flask_security.utils import hash_password
from sqlalchemy import JSON, ARRAY

from enferno.utils.base import BaseMixin
from ..extensions import db

from sqlalchemy.ext.mutable import Mutable

class MutableList(Mutable, list):
    def append(self, value):
        list.append(self, value)
        self.changed()

    def pop(self, index=0):
        value = list.pop(self, index)
        self.changed()
        return value

    @classmethod
    def coerce(cls, key, value):
        if not isinstance(value, MutableList):
            if isinstance(value, list):
                return MutableList(value)
            return Mutable.coerce(key, value)
        else:
            return value



roles_users = db.Table('roles_users',
                       db.Column('user_id', db.Integer(),
                                 db.ForeignKey('user.id')),
                       db.Column('role_id', db.Integer(),
                                 db.ForeignKey('role.id')))


class Role(db.Model, RoleMixin, BaseMixin):
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
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

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color': self.color or ''

        }

    def to_json(self):
        return json.dumps(self.to_dict())

    def from_json(self, jsn):
        self.name = jsn.get('name', '')
        self.description = jsn.get('description', '')
        self.color = jsn.get('color')
        return self

    def __repr__(self):
        return '{} - {}'.format(self.id, self.name)


class User(UserMixin, db.Model, BaseMixin):
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False, default=uuid4().hex)
    name = db.Column(db.String(255))
    picture = db.Column(db.String(255))
    email = db.Column(db.String(255), nullable=True)
    username = db.Column(db.String(255), nullable=True, unique=True)
    password = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=False)
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    # email confirmation
    confirmed_at = db.Column(db.DateTime())
    # tracking
    last_login_at = db.Column(db.DateTime())
    current_login_at = db.Column(db.DateTime())
    last_login_ip = db.Column(db.String(255))
    current_login_ip = db.Column(db.String(255))
    login_count = db.Column(db.Integer())

    tf_phone_number = db.Column(db.String(64))
    tf_primary_method = db.Column(db.String(140))
    tf_totp_secret = db.Column(db.String(255))

    mf_recovery_codes = db.Column(MutableList.as_mutable(ARRAY(db.String) ), nullable=True)

    # individual abilities
    view_usernames = db.Column(db.Boolean, default=True)
    view_simple_history = db.Column(db.Boolean, default=True)
    view_full_history = db.Column(db.Boolean, default=True)
    can_self_assign = db.Column(db.Boolean, default=False)
    can_edit_locations = db.Column(db.Boolean, default=False)
    can_export = db.Column(db.Boolean, default=False)


    # oauth
    google_id = db.Column(db.String(255))

    settings = db.Column(JSON)

    def roles_in(self, roles):
        chk = [self.has_role(r) for r in roles]
        return any(chk)

    def __unicode__(self):
        return '%s' % self.id

    def __repr__(self):
        return "%s %s %s" % (self.name, self.id, self.email)

    @property
    def secure_email(self):
        try:
            if current_user.view_usernames or current_user.has_role('Admin') or current_user is None:
                return self.email
        except Exception as ex:
            pass
        return f'user-{self.id}'

    @property
    def secure_name(self):
        try:
            if current_user.view_usernames or current_user.has_role('Admin') or current_user is None:
                return self.name
        except Exception as ex:
            pass
        return f'user-{self.id}'

    @property
    def secure_username(self):
        try:
            if current_user.view_usernames or current_user.has_role('Admin') or current_user is None:
                return self.username
        except Exception as ex:
            pass
        return f'user-{self.id}'

    def can_access(self, obj):
        """
        check if user can access a specific entity
        :param user: user to check
        :param obj: entity (Bulletin, Actor etc ..)
        :return: True or False based on access roles
        """
        # grant admin access always to restricted items
        if self.has_role('Admin'):
            return True

        # handle primary entities (bulletins, actors, incidents)
        if obj.__tablename__ in ['bulletin','actor','incident']:
            # intersect roles
            if not obj.roles or set(self.roles) & set(obj.roles):
                return True

        # handle media access
        elif obj.__tablename__ == 'media':
            # media can be related to either an actor or a bulletin
            # find out which one
            parent = obj.bulletin or obj.actor
            # Restrict all medias without a parent
            # intersect roles with parent
            if parent and (not parent.roles or set(self.roles) & set(parent.roles)):
                return True
        return False

    def from_json(self, item):

        self.email = item.get('email')
        self.username = item.get('username')

        # check password is not empty
        password = item.get('password')
        if password:
            self.password = hash_password(password)

        self.name = item.get('name')

        # roles
        roles = item.get('roles', [])
        new_roles = []
        if len(roles):
            ids = [r.get('id', -1) for r in roles]
            new_roles = Role.query.filter(Role.id.in_(ids)).all()
            self.roles = new_roles

        # permissions
        self.view_usernames = item.get('view_usernames', False)
        self.view_simple_history = item.get('view_simple_history', False)
        self.view_full_history = item.get('view_full_history', False)
        self.can_self_assign = item.get('can_self_assign', False)
        self.can_edit_locations = item.get('can_edit_locations', False)
        self.can_export = item.get('can_export', False)

        self.active = item.get('active')
        return self

    def to_compact(self):
        """
        Compact serializer for User class. 
        Hides user data from users without 
        permissions.
        """
        return {
            'id': self.id,
            'name': self.secure_name,
            'username': self.secure_username,
            'active': self.active
        }

    def to_dict(self):
        """
        Main serializer for User class.
        """
        return {
                'id': self.id,
                'name': self.secure_name,
                'google_id': self.google_id,
                'email': self.secure_email,
                'username': self.secure_username,
                'active': self.active,
                'roles': [role.to_dict() for role in self.roles],
                'view_usernames': self.view_usernames,
                'view_simple_history': self.view_simple_history,
                'view_full_history': self.view_full_history,
                'can_self_assign': self.can_self_assign,
                'can_edit_locations': self.can_edit_locations,
                'can_export': self.can_export
            }

    def to_json(self):
        return json.dumps(self.to_dict())

    meta = {
        'allow_inheritance': True,
        'indexes': ['-created_at', 'email', 'username'],
        'ordering': ['-created_at']
    }
