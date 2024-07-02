# -*- coding: utf-8 -*-
"""Extensions module. Each extension is initialized in the app factory located
in app.py
"""

from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from flask_redis import FlaskRedis
from flask_babel import Babel
from flask_debugtoolbar import DebugToolbarExtension

db = SQLAlchemy()
session = Session()
rds = FlaskRedis()
babel = Babel()
debug_toolbar = DebugToolbarExtension()
