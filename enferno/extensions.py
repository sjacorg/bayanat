# -*- coding: utf-8 -*-
"""Extensions module. Each extension is initialized in the app factory located
in app.py
"""

from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_debugtoolbar import DebugToolbarExtension
from flask_session import Session
from flask_bouncer import Bouncer
from flask_redis import FlaskRedis
from flask_babel import Babel

db = SQLAlchemy()
cache = Cache()
debug_toolbar = DebugToolbarExtension()
session = Session()
bouncer = Bouncer()
rds = FlaskRedis()
babel = Babel()