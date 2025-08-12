# -*- coding: utf-8 -*-
"""Extensions module. Each extension is initialized in the app factory located
in app.py
"""

from flask_limiter.util import get_remote_address
from flask_limiter import Limiter
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from flask_redis import FlaskRedis
from flask_babel import Babel
from flask_debugtoolbar import DebugToolbarExtension
from flask_mail import Mail

from enferno.utils.rate_limit_utils import get_real_ip
from enferno.settings import Config as cfg

db = SQLAlchemy()
session = Session()
rds = FlaskRedis()
babel = Babel()
debug_toolbar = DebugToolbarExtension()
mail = Mail()
limiter = Limiter(
    key_func=get_real_ip,
    strategy="moving-window",
    headers_enabled=True,
    retry_after="delta-seconds",
    storage_uri=cfg.REDIS_URL,
)
