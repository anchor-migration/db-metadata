"""CLI entry point for db-migration tool."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from db_migration.config import parse_schemas, resolve_url
from db_migration.extract.inspector import extract_metadata
from db_migration.store.writer import MetadataWriter, init_db, read_info

app = typer.Typer(
    name="db-migration",
    help="Export database metadata from live databases to local SQLite SSoT.",
    no_args_is_help=True,
)


@app.command("export")
def export_cmd(
    url: Optional[str] = typer.Option(
        None,
        "--url",
        "-u",
        help="SQLAlchemy database URL (or set DB_MIGRATION_URL)",
    ),
    schemas: Optional[str] = typer.Option(
        None,
        "--schemas",
        "-s",
        help="Comma-separated schema names to export (default: all user schemas)",
    ),
    out: Path = typer.Option(
        ...,
        "--out",
        "-o",
        help="Output SQLite file path",
    ),
) -> None:
    """Export metadata from a live database to SQLite."""
    db_url = resolve_url(url)
    schema_filter = parse_schemas(schemas)

    typer.echo(f"Connecting to {db_url.split('@')[-1] if '@' in db_url else 'database'}...")
    snapshot = extract_metadata(db_url, schema_filter)

    schema_count = len(snapshot.schemas)
    table_count = sum(len(s.tables) for s in snapshot.schemas)
    typer.echo(f"Extracted {schema_count} schema(s), {table_count} table(s)/view(s)")

    writer = MetadataWriter(out)
    export_run_id = writer.write(snapshot)
    typer.echo(f"Written to {out} (export_run_id={export_run_id})")


@app.command("init-db")
def init_db_cmd(
    out: Path = typer.Option(
        ...,
        "--out",
        "-o",
        help="SQLite file path to initialize",
    ),
) -> None:
    """Initialize an empty SQLite metadata database (DDL only)."""
    init_db(out)
    typer.echo(f"Initialized {out}")


@app.command("info")
def info_cmd(
    db_path: Path = typer.Argument(..., help="SQLite metadata file path"),
    export_run_id: Optional[int] = typer.Option(
        None,
        "--run-id",
        help="Specific export_run id (default: latest)",
    ),
) -> None:
    """Show summary of an exported metadata database."""
    info = read_info(db_path, export_run_id)
    typer.echo(f"Export run:     {info.export_run_id}")
    typer.echo(f"Source dialect: {info.source_dialect}")
    typer.echo(f"Exported at:    {info.exported_at}")
    typer.echo(f"Schemas:        {info.schema_count}")
    typer.echo(f"Tables/views:   {info.table_count}")
    typer.echo(f"Columns:        {info.column_count}")
    typer.echo(f"Foreign keys:   {info.foreign_key_count}")
    typer.echo(f"Indexes:        {info.index_count}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
