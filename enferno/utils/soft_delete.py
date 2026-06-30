"""Global soft-delete filter for Media.

`deleted` lives on BaseMixin so every model carries it, but only Media is
actually soft-deleted in practice. Rather than remembering a manual
`.filter(deleted == False)` at every read site (the source of recurring
"deleted media still shows up" bugs), this injects the predicate into every
ORM SELECT that touches Media, including lazy relationship loads such as
`bulletin.medias`.

Opt out for the rare route that must reach an already-deleted row by id:

    Media.query.execution_options(include_deleted=True).get(id)
"""

from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria

from enferno.admin.models import Media


def _filter_soft_deleted_media(state):
    if (
        state.is_select
        and not state.is_column_load
        and not state.execution_options.get("include_deleted", False)
    ):
        state.statement = state.statement.options(
            with_loader_criteria(Media, Media.deleted.is_(False), include_aliases=True)
        )


def register_soft_delete(db):
    """Attach the soft-delete filter to the session. Idempotent."""
    if not event.contains(Session, "do_orm_execute", _filter_soft_deleted_media):
        event.listen(Session, "do_orm_execute", _filter_soft_deleted_media)
