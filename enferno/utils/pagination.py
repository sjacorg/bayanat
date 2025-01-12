from typing import TypeVar, Generic, List, Optional, Any, Dict, Tuple
from sqlalchemy import select, func
from sqlalchemy.sql import Select
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

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
    query: Select, db_session, per_page: int, cursor: Optional[str] = None, id_column=None
) -> CursorPaginationResult:
    """
    Generic cursor-based pagination for SQLAlchemy queries.

    Args:
        query: Base SQLAlchemy select statement
        db_session: SQLAlchemy session
        per_page: Number of items per page
        cursor: Optional cursor for pagination
        id_column: Column to use for cursor (defaults to model's id column)

    Returns:
        CursorPaginationResult containing paginated items and metadata
    """
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = db_session.execute(count_query).scalar()

    # Apply cursor if provided
    if cursor:
        query = query.where(id_column < int(cursor))

    # Get one extra item to determine if there's a next page
    query = query.limit(per_page + 1)

    # Execute query
    items = db_session.execute(query).scalars().all()

    # Handle pagination metadata
    has_next = len(items) > per_page
    if has_next:
        items = items[:-1]
        next_cursor = str(items[-1].id)
    else:
        next_cursor = None

    return CursorPaginationResult(
        items=items, total=total, per_page=per_page, has_next=has_next, next_cursor=next_cursor
    )
