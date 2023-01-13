import json
from uuid import uuid4

from flask_security import UserMixin, RoleMixin
from flask_security import current_user
from flask_security.utils import hash_password
from sqlalchemy import JSON

from enferno.utils.base import BaseMixin
from ..extensions import db

roles_users = db.Table('roles_users',
                       db.Column('user_id', db.Integer(),
                                 db.ForeignKey('user.id')),
                       db.Column('role_id', db.Integer(),
                                 db.ForeignKey('role.id')))


class Role(db.Model, RoleMixin, BaseMixin):
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
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

        }

    def to_json(self):
        return json.dumps(self.to_dict())

    def from_json(self, json):
        self.name = json.get('name', '')
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

    # individual abilities
    view_usernames = db.Column(db.Boolean, default=True)
    view_simple_history = db.Column(db.Boolean, default=True)
    view_full_history = db.Column(db.Boolean, default=True)
    can_self_assign = db.Column(db.Boolean, default=False)
    can_edit_locations = db.Column(db.Boolean, default=False)

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

    def from_json(self, item):
        self.email = item.get('email')
        self.username = item.get('username')
        password = item.get('password')
        self.password = hash_password(password)
        self.name = item.get('name')
        roles = item.get('roles', [])
        rs = []
        if len(roles):
            ids = [r.get('id', -1) for r in roles]
            rs = Role.query.filter(Role.id.in_(ids)).all()
            self.roles = rs

        self.view_usernames = item.get('view_usernames', False)
        self.view_simple_history = item.get('view_simple_history', False)
        self.view_full_history = item.get('view_full_history', False)
        self.can_self_assign = item.get('can_self_assign', False)
        self.can_edit_locations = item.get('can_edit_locations', False)

        self.active = item['active']
        return self

    def to_compact(self):

        """Automatically detect permissions of the user"""

        try:
            hide = True
            if current_user.view_usernames or current_user.has_role('Admin'):
                hide = False
        except Exception:
            hide = True

        if hide:
            name = ''
            username = ''
        else:
            name = self.name
            username = self.username


        return {
            'id': self.id,
            'name': name,
            'username': username,
            'active': self.active

        }

    def to_dict(self, hide_name=False):
        name = self.name
        if hide_name:
            name = ''
            email = ''
            name = ''

        return {
                'id': self.id,
                'name': name,
                'google_id': self.google_id,
                'email': self.email,
                'username': self.username ,
                'active': self.active,
                'roles': [role.to_dict() for role in self.roles],
                'view_usernames': self.view_usernames,
                'view_simple_history': self.view_simple_history,
                'view_full_history': self.view_full_history,
                'can_self_assign': self.can_self_assign,
                'can_edit_locations': self.can_edit_locations

            }

    def to_json(self):
        return json.dumps(self.to_dict())

    meta = {
        'allow_inheritance': True,
        'indexes': ['-created_at', 'email', 'username'],
        'ordering': ['-created_at']
    }
