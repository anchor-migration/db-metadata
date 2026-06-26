"""Write extracted metadata snapshots to SQLite."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from db_migration import __version__
from db_migration.config import stable_column_id, stable_table_id
from db_migration.models.metadata import DatabaseSnapshot


def _schema_sql_path() -> str:
    ref = resources.files("db_migration.store") / "schema" / "v1.sql"
    with resources.as_file(ref) as path:
        return str(path)


def init_db(db_path: str | Path) -> None:
    """Create or upgrade SQLite file with metadata DDL."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        with open(_schema_sql_path(), encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
    finally:
        conn.close()


@dataclass
class ExportInfo:
    export_run_id: int
    source_dialect: str
    exported_at: str
    schema_count: int
    table_count: int
    column_count: int
    foreign_key_count: int
    index_count: int


def read_info(db_path: str | Path, export_run_id: int | None = None) -> ExportInfo:
    """Read summary for latest or specific export run."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        if export_run_id is None:
            row = conn.execute(
                "SELECT id FROM export_run ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row is None:
                raise ValueError(f"No export runs found in {db_path}")
            export_run_id = row["id"]

        run = conn.execute(
            "SELECT id, source_dialect, exported_at FROM export_run WHERE id = ?",
            (export_run_id,),
        ).fetchone()
        if run is None:
            raise ValueError(f"Export run {export_run_id} not found")

        schema_count = conn.execute(
            "SELECT COUNT(*) FROM db_schema WHERE export_run_id = ?",
            (export_run_id,),
        ).fetchone()[0]
        table_count = conn.execute(
            "SELECT COUNT(*) FROM db_table WHERE export_run_id = ?",
            (export_run_id,),
        ).fetchone()[0]
        column_count = conn.execute(
            "SELECT COUNT(*) FROM db_column WHERE export_run_id = ?",
            (export_run_id,),
        ).fetchone()[0]
        foreign_key_count = conn.execute(
            "SELECT COUNT(*) FROM db_foreign_key WHERE export_run_id = ?",
            (export_run_id,),
        ).fetchone()[0]
        index_count = conn.execute(
            "SELECT COUNT(*) FROM db_index WHERE export_run_id = ?",
            (export_run_id,),
        ).fetchone()[0]

        return ExportInfo(
            export_run_id=export_run_id,
            source_dialect=run["source_dialect"],
            exported_at=run["exported_at"],
            schema_count=schema_count,
            table_count=table_count,
            column_count=column_count,
            foreign_key_count=foreign_key_count,
            index_count=index_count,
        )
    finally:
        conn.close()


class MetadataWriter:
    """Persist a DatabaseSnapshot into SQLite."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        init_db(self.db_path)

    def write(self, snapshot: DatabaseSnapshot) -> int:
        """Write snapshot as new export_run. Returns export_run id."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            export_run_id = self._insert_export_run(conn, snapshot)
            table_key_map: dict[str, int] = {}

            for schema in snapshot.schemas:
                schema_id = self._insert_schema(conn, export_run_id, schema.name)
                for table in schema.tables:
                    stable_tid = stable_table_id(schema.name, table.name)
                    table_id = self._insert_table(
                        conn,
                        export_run_id,
                        schema_id,
                        schema.name,
                        table,
                    )
                    table_key_map[stable_tid] = table_id
                    self._insert_columns(conn, export_run_id, schema.name, table, table_id)
                    self._insert_primary_keys(conn, export_run_id, table, table_id)
                    self._insert_indexes(conn, export_run_id, table, table_id)
                    self._insert_unique_constraints(conn, export_run_id, table, table_id)

            for schema in snapshot.schemas:
                for table in schema.tables:
                    source_stable = stable_table_id(schema.name, table.name)
                    source_table_id = table_key_map[source_stable]
                    for fk in table.foreign_keys:
                        target_stable = stable_table_id(fk.target_schema, fk.target_table)
                        target_table_id = table_key_map.get(target_stable)
                        if target_table_id is None:
                            continue
                        self._insert_foreign_key(
                            conn,
                            export_run_id,
                            fk,
                            source_table_id,
                            target_table_id,
                        )

            conn.commit()
            return export_run_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _insert_export_run(self, conn: sqlite3.Connection, snapshot: DatabaseSnapshot) -> int:
        cursor = conn.execute(
            """
            INSERT INTO export_run (source_dialect, source_url_masked, schema_filter, tool_version)
            VALUES (?, ?, ?, ?)
            """,
            (
                snapshot.source_dialect,
                snapshot.source_url_masked,
                snapshot.schema_filter,
                __version__,
            ),
        )
        return cursor.lastrowid

    def _insert_schema(self, conn: sqlite3.Connection, export_run_id: int, name: str) -> int:
        cursor = conn.execute(
            "INSERT INTO db_schema (export_run_id, name) VALUES (?, ?)",
            (export_run_id, name),
        )
        return cursor.lastrowid

    def _insert_table(
        self,
        conn: sqlite3.Connection,
        export_run_id: int,
        schema_id: int,
        schema_name: str,
        table,
    ) -> int:
        cursor = conn.execute(
            """
            INSERT INTO db_table (schema_id, export_run_id, name, table_type, comment, stable_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                schema_id,
                export_run_id,
                table.name,
                table.table_type,
                table.comment,
                stable_table_id(schema_name, table.name),
            ),
        )
        return cursor.lastrowid

    def _insert_columns(
        self,
        conn: sqlite3.Connection,
        export_run_id: int,
        schema_name: str,
        table,
        table_id: int,
    ) -> None:
        for col in table.columns:
            conn.execute(
                """
                INSERT INTO db_column (
                    table_id, export_run_id, name, ordinal, data_type, full_type,
                    nullable, default_value, comment, is_pk, stable_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    table_id,
                    export_run_id,
                    col.name,
                    col.ordinal,
                    col.data_type,
                    col.full_type,
                    1 if col.nullable else 0,
                    col.default_value,
                    col.comment,
                    1 if col.is_pk else 0,
                    stable_column_id(schema_name, table.name, col.name),
                ),
            )

    def _insert_primary_keys(
        self,
        conn: sqlite3.Connection,
        export_run_id: int,
        table,
        table_id: int,
    ) -> None:
        for pk in table.primary_keys:
            conn.execute(
                """
                INSERT INTO db_primary_key (table_id, export_run_id, column_name, ordinal)
                VALUES (?, ?, ?, ?)
                """,
                (table_id, export_run_id, pk.column_name, pk.ordinal),
            )

    def _insert_foreign_key(
        self,
        conn: sqlite3.Connection,
        export_run_id: int,
        fk,
        source_table_id: int,
        target_table_id: int,
    ) -> None:
        conn.execute(
            """
            INSERT INTO db_foreign_key (
                export_run_id, name, source_table_id, source_column,
                target_table_id, target_column, on_delete, on_update
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                export_run_id,
                fk.name,
                source_table_id,
                fk.source_column,
                target_table_id,
                fk.target_column,
                fk.on_delete,
                fk.on_update,
            ),
        )

    def _insert_indexes(
        self,
        conn: sqlite3.Connection,
        export_run_id: int,
        table,
        table_id: int,
    ) -> None:
        for index in table.indexes:
            cursor = conn.execute(
                """
                INSERT INTO db_index (table_id, export_run_id, name, is_unique)
                VALUES (?, ?, ?, ?)
                """,
                (table_id, export_run_id, index.name, 1 if index.unique else 0),
            )
            index_id = cursor.lastrowid
            for col in index.columns:
                conn.execute(
                    """
                    INSERT INTO db_index_column (
                        index_id, export_run_id, column_name, ordinal, sort_order
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (index_id, export_run_id, col.column_name, col.ordinal, col.sort_order),
                )

    def _insert_unique_constraints(
        self,
        conn: sqlite3.Connection,
        export_run_id: int,
        table,
        table_id: int,
    ) -> None:
        for uc in table.unique_constraints:
            for ordinal, column_name in enumerate(uc.columns, start=1):
                conn.execute(
                    """
                    INSERT INTO db_unique_constraint (
                        table_id, export_run_id, name, column_name, ordinal
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (table_id, export_run_id, uc.name, column_name, ordinal),
                )
