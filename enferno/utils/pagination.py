from typing import TypeVar, Generic, List, Optional, Any, Dict
from sqlalchemy import select, func
from sqlalchemy.sql import Select
from dataclasses import dataclass
from sqlalchemy.orm import DeclarativeBase
from enferno.extensions import db

T = TypeVar("T", bound=DeclarativeBase)


@dataclass
class CursorPaginationResult(Generic[T]):
    """Represents paginated results with cursor-based navigation."""

    items: List[T]
    total: int
    per_page: int
    has_next: bool
    next_cursor: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert pagination result to dictionary format."""
        return {
            "items": self.items,
            "total": self.total,
            "perPage": self.per_page,
            "hasNext": self.has_next,
            "nextCursor": self.next_cursor,
        }


def paginate_query(
    query: Select, per_page: int, cursor: Optional[str] = None, id_column=None
) -> CursorPaginationResult:
    """Generic cursor-based pagination for SQLAlchemy queries."""
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = db.session.execute(count_query).scalar()

    # Always order by id descending for consistent pagination
    query = query.order_by(id_column.desc())

    # If cursor provided, get items with id strictly less than cursor
    if cursor:
        query = query.where(id_column < int(cursor))  # Strict less than to avoid duplicates

    # Get one extra item to determine if there's a next page
    items = db.session.execute(query.limit(per_page + 1)).scalars().all()

    # Handle pagination metadata
    has_next = len(items) > per_page
    if has_next:
        items = items[:-1]  # Remove the extra item
        next_cursor = str(items[-1].id) if items else None
    else:
        next_cursor = None

    return CursorPaginationResult(
        items=items, total=total, per_page=per_page, has_next=has_next, next_cursor=next_cursor
    )
