# -*- coding: utf-8 -*-
"""Click commands."""
import os

import click
from flask.cli import AppGroup
from flask.cli import with_appcontext
from flask_security.utils import hash_password

from enferno.extensions import db
from enferno.user.models import User


@click.command()
@with_appcontext
def create_db():
    """creates db tables - import your models within commands.py to create the models.
    """
    db.engine.execute('CREATE EXTENSION if not exists pg_trgm ;')
    print('Trigram extension installed successfully')
    db.engine.execute('CREATE EXTENSION if not exists postgis ;')
    print('Postgis extension installed successfully')
    db.create_all()
    print('Database structure created successfully')

    # possible optimization: SET enable_seqscan = off;


@click.command()
@with_appcontext
def install():
    """Install a default Admin user and add an Admin role to it.
    """
    # check if admin exists
    from enferno.user.models import Role
    a = Role.query.filter(Role.name == 'Admin').first()
    if a is None:
        # create admin role
        r = Role(name='Admin')
        r.save()
        u = click.prompt('Admin username?', default='admin')
        p = click.prompt('Admin Password (min 6 characters)?')
        user = User(username=u, password=hash_password(p), active=1)
        user.name = 'Admin'
        user.roles.append(r)
        user.save()

    else:
        print('Seems like an Admin is already installed')


@click.command()
@click.option('-u', '--username', prompt=True, default=None)
@click.option('-p', '--password', prompt=True, default=None)
@with_appcontext
def create(username, password):
    """Creates a user using an email.
    """
    a = User.query.filter(User.username == username).first()
    if a:
        print('User already exists!')

    user = User(username=username,  password=hash_password(password), active=1)
    user.save()
    print('User created successfully')


@click.command()
@click.option('-e', '--email', prompt=True, default=None)
@click.option('-r', '--role', prompt=True, default='Admin')
@with_appcontext
def add_role(email, role):
    """Adds a role to the specified user.
        """
    from enferno.user.models import Role
    u = User.query.filter(User.email == email).first()

    if u is None:
        print('Sorry, this user does not exist!')
    else:
        r = Role.query.filter(Role.name == role).first()
        if r is None:
            print('Sorry, this role does not exist!')
            u = click.prompt('Would you like to create one? Y/N', default='N')
            if u.lower() == 'y':
                r = Role(name=role)
                try:
                    db.session.add(r)
                    db.session.commit()
                    print('Role created successfully, you may add it now to the user')
                except Exception as e:
                    db.session.rollback()
        # add role to user
        u.roles.append(r)


@click.command()
@click.option('-e', '--email', prompt=True, default=None)
@click.option('-p', '--password', hide_input=True, confirmation_prompt=True, prompt=True, default=None)
@with_appcontext
def reset(email, password):
    """Reset a user password
    """
    try:
        pwd = hash_password(password)
        u = User.query.filter(User.email == email).first()
        u.password = pwd
        u.save()
        print('User password has been reset successfully.')

    except Exception as e:
        print('Error resetting user password: %s' % e)


@click.command()
def clean():
    """Remove *.pyc and *.pyo files recursively starting at current directory.
    Borrowed from Flask-Script, converted to use Click.
    """
    for dirpath, dirnames, filenames in os.walk('.'):
        for filename in filenames:
            if filename.endswith('.pyc') or filename.endswith('.pyo'):
                full_pathname = os.path.join(dirpath, filename)
                click.echo('Removing {}'.format(full_pathname))
                os.remove(full_pathname)


# translation management
i18n_cli = AppGroup('translate', short_help='commands to help with translation management')


@i18n_cli.command()
def extract():
    if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'):
        raise RuntimeError('Extract command failed')


@i18n_cli.command()
def update():
    if os.system('pybabel update -i messages.pot -d enferno/translations'):
        raise RuntimeError('Update command failed')


@i18n_cli.command()
def compile():
    if os.system('pybabel compile -d enferno/translations'):
        raise RuntimeError('Compile command failed')
