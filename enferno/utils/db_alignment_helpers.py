import warnings
from typing import Any

import click
from sqlalchemy import MetaData, inspect, create_engine, text
from sqlalchemy.engine import Engine

from enferno.extensions import db
from enferno.settings import Config
from enferno.utils.logging_utils import get_logger

logger = get_logger()


class DBAlignmentChecker:
    """Check alignment of the database schema with SQLAlchemy models."""

    def __init__(self):
        self.engine: Engine = create_engine(Config.get("SQLALCHEMY_DATABASE_URI"))
        warnings.filterwarnings("ignore", message="Did not recognize type")
        self.metadata = MetaData()
        self.metadata.reflect(self.engine)
        self.inspector = inspect(self.engine)
        self.model_classes = self._get_model_classes()
        self.db_tables = set(self.metadata.tables.keys())
        self.joint_tables = self._get_joint_tables()

    def _type_check(self, model_type: Any, db_type: Any) -> bool:
        return isinstance(model_type, type(db_type)) or isinstance(db_type, type(model_type))

    def _get_model_classes(self) -> list:
        return [(model, model.__tablename__) for model in db.Model.__subclasses__()]

    def _get_joint_tables(self) -> set:
        joint_tables = set()
        for model, _ in self.model_classes:
            for attr in dir(model):
                if attr.startswith("_"):
                    continue
                field = getattr(model, attr)
                if hasattr(field, "property") and hasattr(field.property, "mapper"):
                    if field.property.secondary is not None:
                        joint_tables.add(field.property.secondary.name)
        return joint_tables

    def _report_table_discrepancies(self, model, table_name: str) -> list:
        """Return list of (level, message) tuples for discrepancies."""
        issues = []
        table = self.metadata.tables.get(table_name)
        if table is None:
            issues.append(
                ("error", f"Table '{table_name}' for model {model.__name__} does not exist")
            )
            return issues

        model_columns = {c.name: c.type for c in model.__table__.columns}
        table_columns = {c.name: c.type for c in table.columns}

        for name, model_type in model_columns.items():
            if name not in table_columns:
                issues.append(("warning", f"Column '{name}' missing in table '{table_name}'"))
            elif not self._type_check(model_type, table_columns[name]):
                issues.append(
                    (
                        "warning",
                        f"Type mismatch '{name}' in '{table_name}': model={model_type} db={table_columns[name]}",
                    )
                )

        for name in table_columns:
            if name not in model_columns:
                issues.append(
                    ("info", f"Extra column '{name}' in table '{table_name}', not in model")
                )

        return issues

    def _check_dynamic_fields(self) -> list:
        """Check dynamic field columns exist in their entity tables."""
        issues = []
        try:
            from enferno.admin.models.DynamicField import DynamicField

            active_fields = DynamicField.query.filter(
                DynamicField.active.is_(True), DynamicField.core.is_(False)
            ).all()

            for field in active_fields:
                table_name = field.entity_type
                if table_name not in self.db_tables:
                    issues.append(
                        ("warning", f"Dynamic field '{field.name}': table '{table_name}' not found")
                    )
                    continue
                db_columns = {c["name"] for c in self.inspector.get_columns(table_name)}
                if field.name not in db_columns:
                    issues.append(
                        (
                            "warning",
                            f"Dynamic field '{field.name}': column missing in '{table_name}'",
                        )
                    )
        except Exception as e:
            issues.append(("warning", f"Could not check dynamic fields: {e}"))
        return issues

    def _check_migration_status(self) -> list:
        """Check if Alembic migrations are up to date."""
        issues = []
        try:
            import logging as _logging
            from alembic.migration import MigrationContext
            from alembic.script import ScriptDirectory
            from enferno.extensions import migrate as migrate_ext

            _logging.getLogger("alembic.runtime.migration").setLevel(_logging.WARNING)

            config = migrate_ext.get_config()
            script = ScriptDirectory.from_config(config)
            head = script.get_current_head()

            context = MigrationContext.configure(db.session.connection())
            current = context.get_current_heads()
            current_rev = current[0] if current else None

            if current_rev is None:
                issues.append(("warning", "No Alembic revision stamped (run: flask db upgrade)"))
            elif current_rev == head:
                issues.append(("ok", "Migrations up to date"))
            else:
                issues.append(
                    ("error", f"Pending migrations (current: {current_rev[:8]}, head: {head[:8]})")
                )
        except Exception as e:
            issues.append(("warning", f"Could not check migration status: {e}"))
        return issues

    def check_db_alignment(self) -> None:
        """Run all checks and print results."""
        errors = 0
        warns = 0

        click.echo("\nMigrations:")
        for level, msg in self._check_migration_status():
            if level == "ok":
                click.echo(f"  + {msg}")
            elif level == "error":
                click.echo(click.style(f"  - {msg}", fg="red"))
                errors += 1
            else:
                click.echo(click.style(f"  ! {msg}", fg="yellow"))
                warns += 1

        click.echo("\nSchema:")
        has_issues = False
        for model, table_name in self.model_classes:
            for level, msg in self._report_table_discrepancies(model, table_name):
                has_issues = True
                if level == "error":
                    click.echo(click.style(f"  - {msg}", fg="red"))
                    errors += 1
                elif level == "warning":
                    click.echo(click.style(f"  ! {msg}", fg="yellow"))
                    warns += 1
                else:
                    click.echo(f"    {msg}")

        if not has_issues:
            click.echo("  + All tables aligned with models")

        extra_tables = self.db_tables - {name for _, name in self.model_classes} - self.joint_tables
        extra_tables = {t for t in extra_tables if not t.startswith("spatial_")}
        if extra_tables:
            click.echo(f"\n  Extra tables (not in models): {', '.join(sorted(extra_tables))}")

        click.echo("\nDynamic Fields:")
        df_issues = self._check_dynamic_fields()
        if df_issues:
            for level, msg in df_issues:
                if level == "warning":
                    click.echo(click.style(f"  ! {msg}", fg="yellow"))
                    warns += 1
                else:
                    click.echo(f"    {msg}")
        else:
            click.echo("  + All dynamic field columns present")

        click.echo()
        if errors:
            click.echo(click.style(f"{errors} errors, {warns} warnings", fg="red"))
        elif warns:
            click.echo(click.style(f"{warns} warnings, no errors", fg="yellow"))
        else:
            click.echo("Database is aligned with the schema")
