from typing import TypeVar, Generic, List, Optional, Any, Dict
from enferno.utils.logging_utils import get_logger

logger = get_logger()

T = TypeVar("T")


class PaginationResult(Generic[T]):
    """A generic class that handles pagination results with typed items.

    Stores paginated items along with metadata like total count and cursor information.
    """

    def __init__(
        self,
        items: List[T],
        total: Optional[int] = None,
        next_cursor: Optional[str] = None,
        per_page: int = 20,
    ):
        """Initialize a new PaginationResult instance.

        Args:
            items: List of paginated items
            total: Optional total count of all items
            next_cursor: Optional cursor for next page
            per_page: Number of items per page (default: 20)
        """
        self.items = items
        self.total = total
        self.next_cursor = next_cursor
        self.per_page = per_page

    def to_dict(self) -> Dict[str, Any]:
        """Convert pagination result to a dictionary format for frontend use.

        Returns:
            Dict containing items, total count, items per page, and next cursor
        """
        return {
            "items": self.items,
            "total": self.total if self.total is not None else len(self.items),
            "perPage": self.per_page,
            "nextCursor": self.next_cursor,
        }


def paginate_query(
    query,
    per_page: int = 20,
    cursor: Optional[str] = None,
    cursor_column: str = "id",
    descending: bool = True,
) -> PaginationResult:
    """Paginate a database query using cursor-based pagination.

    Args:
        query: The database query to paginate
        per_page: Number of items per page
        cursor: Optional cursor value for pagination
        cursor_column: Column name to use for cursor (default: 'id')
        descending: Sort order (default: True for DESC)

    Returns:
        PaginationResult containing the paginated items and metadata
    """
    model_class = query.column_descriptions[0]["type"]

    # Apply consistent sorting
    query = query.order_by(
        getattr(model_class, cursor_column).desc()
        if descending
        else getattr(model_class, cursor_column).asc()
    )

    # Handle cursor-based filtering
    if cursor:
        try:
            cursor_value = int(cursor)
            operator = "<" if descending else ">"
            filtered_query = query.filter(
                getattr(model_class, cursor_column).__lt__(cursor_value)
                if descending
                else getattr(model_class, cursor_column).__gt__(cursor_value)
            )
            logger.debug(f"SQL Query: {filtered_query}")
            items = filtered_query.limit(per_page + 1).all()
        except (ValueError, TypeError):
            items = query.limit(per_page + 1).all()
    else:
        items = query.limit(per_page + 1).all()

    # Determine if there's a next page and prepare next cursor
    has_next = len(items) > per_page
    if has_next:
        items = items[:-1]  # Remove the extra item we fetched
        next_cursor = str(getattr(items[-1], cursor_column))
    else:
        next_cursor = None

    return PaginationResult(items=items, total=None, next_cursor=next_cursor, per_page=per_page)
