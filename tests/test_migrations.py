from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_single_alembic_head():
    """Guard against two branches each parenting a migration on the same revision.

    Git merges such branches cleanly (different files), but the result has two heads
    and `flask db upgrade` aborts mid-deploy. Fix by re-parenting the newer migration
    onto the current head, or `alembic merge heads` if both have already been applied.
    """
    config = Config()
    config.set_main_option(
        "script_location", str(Path(__file__).resolve().parent.parent / "migrations")
    )
    heads = ScriptDirectory.from_config(config).get_heads()

    assert len(heads) == 1, f"Expected a single Alembic head, found {len(heads)}: {heads}"
