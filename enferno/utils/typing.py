from typing import TypeVar
from sqlalchemy.ext.declarative import DeclarativeMeta


typ = type
id = int
Model = TypeVar("Model", bound=DeclarativeMeta)
