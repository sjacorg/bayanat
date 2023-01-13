# -*- coding: utf-8 -*-
"""Extensions module. Each extension is initialized in the app factory located
in app.py
"""

from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_mail import Mail
from flask_debugtoolbar import DebugToolbarExtension
from flask_session import Session
from flask_bouncer import Bouncer
from enferno.settings import Config
from redis import Redis
from flask_babelex import Babel

db = SQLAlchemy()
cache = Cache()
mail = Mail()
debug_toolbar = DebugToolbarExtension()
session = Session()
bouncer = Bouncer()
rds = Redis(db=Config.REDIS_BULK_DB, decode_responses=True)
babel = Babel()