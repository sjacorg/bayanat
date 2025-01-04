from typing import TypeVar, Generic, List, Optional, Any, Dict
from sqlalchemy import select, func
from sqlalchemy.orm import Query

T = TypeVar("T")


class PaginationResult(Generic[T]):
    def __init__(
        self,
        items: List[T],
        total: Optional[int] = None,
        next_cursor: Optional[str] = None,
        per_page: int = 20,
    ):
        self.items = items
        self.total = total
        self.next_cursor = next_cursor
        self.per_page = per_page

    def to_dict(self) -> Dict[str, Any]:
        """Convert to format compatible with frontend"""
        return {
            "items": self.items,
            "total": self.total if self.total is not None else len(self.items),
            "perPage": self.per_page,
            "nextCursor": self.next_cursor,
        }


def paginate_query(
    query: Query,
    page: int = 1,
    per_page: int = 20,
    cursor: Optional[str] = None,
    cursor_column: str = "id",
    estimate_count: bool = True,
) -> PaginationResult:
    """
    Flexible pagination that supports both cursor and offset based pagination

    Args:
        query: SQLAlchemy query object
        page: Page number for offset pagination
        per_page: Items per page
        cursor: Optional cursor value for cursor-based pagination
        cursor_column: Column to use for cursor pagination
        estimate_count: Whether to use estimated count for better performance
    """
    # If cursor provided, use cursor-based pagination
    if cursor:
        # Decode cursor value
        cursor_value = cursor

        # Add cursor filter
        filtered_query = query.filter(
            getattr(query.column_descriptions[0]["type"], cursor_column) > cursor_value
        )

        # Get items
        items = filtered_query.limit(per_page + 1).all()

        # Check if there are more items
        has_next = len(items) > per_page
        if has_next:
            items = items[:-1]
            next_cursor = str(getattr(items[-1], cursor_column))
        else:
            next_cursor = None

        # Add estimated count
        total = None
        if estimate_count:
            total = query.session.scalar(select(func.count()).select_from(query.subquery()))

        return PaginationResult(
            items=items, total=total, next_cursor=next_cursor, per_page=per_page
        )

    # Otherwise use offset pagination
    else:
        offset = (page - 1) * per_page

        # Get items for current page plus one extra to check if there's more
        items = query.offset(offset).limit(per_page + 1).all()

        # Check if there are more items
        has_next = len(items) > per_page
        if has_next:
            items = items[:-1]
            next_cursor = str(getattr(items[-1], cursor_column))
        else:
            next_cursor = None

        # Always use fast statistics-based counting
        total = None
        if estimate_count:
            total = query.session.scalar(select(func.count()).select_from(query.subquery()))

        return PaginationResult(
            items=items, total=total, next_cursor=next_cursor, per_page=per_page
        )
