"""Create bani_search and apply sql/schema.sql using documented .env credentials."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
PORT = int(os.getenv("MYSQL_PORT", "3306"))
APP_USER = os.getenv("MYSQL_USER", "banidb")
APP_PASSWORD = os.getenv("MYSQL_PASSWORD", "banidb")
DATABASE = os.getenv("MYSQL_DATABASE", "bani_search")
ROOT_PASSWORD = os.getenv("MYSQL_ROOT_PASSWORD", "root")
SCHEMA = ROOT / "sql" / "schema.sql"


def connect(**kwargs):
    return mysql.connector.connect(
        host=HOST,
        port=PORT,
        charset="utf8mb4",
        collation="utf8mb4_0900_ai_ci",
        autocommit=True,
        use_unicode=True,
        **kwargs,
    )


def try_connect(user: str, password: str, database: str | None = None):
    kwargs = {"user": user, "password": password}
    if database:
        kwargs["database"] = database
    return connect(**kwargs)


def ensure_database(admin) -> None:
    cursor = admin.cursor()
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{DATABASE}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    cursor.close()


def split_sql(sql: str) -> list[str]:
    without_comments: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        without_comments.append(line)
    statements: list[str] = []
    for raw in "\n".join(without_comments).split(";"):
        stmt = raw.strip()
        if stmt:
            statements.append(stmt)
    return statements


def apply_schema(connection) -> None:
    sql = SCHEMA.read_text(encoding="utf-8")
    cursor = connection.cursor()
    for stmt in split_sql(sql):
        cursor.execute(stmt)
        if cursor.with_rows:
            cursor.fetchall()
    cursor.close()


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s",
        (DATABASE, table, column),
    )
    return cursor.fetchone() is not None


def _index_exists(cursor, table: str, index_name: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND INDEX_NAME=%s LIMIT 1",
        (DATABASE, table, index_name),
    )
    return cursor.fetchone() is not None


def ensure_schema_extras(connection) -> None:
    """Add Amrit Keertan columns/indexes to tables created before those extras existed."""
    cursor = connection.cursor()
    verse_columns = [
        ("index_id", "BIGINT NULL"),
        ("header_id", "INT NULL"),
        ("ang", "INT NULL"),
        ("source_page_no", "INT NULL"),
        ("original_source_id", "CHAR(1) NULL"),
        ("original_source_english", "VARCHAR(128) NULL"),
        ("original_source_gurmukhi", "VARCHAR(256) NULL"),
        ("original_source_unicode", "VARCHAR(256) NULL"),
    ]
    search_columns = [
        ("index_id", "BIGINT NULL"),
        ("header_id", "INT NULL"),
        ("ang", "INT NULL"),
        ("original_source_id", "CHAR(1) NULL"),
        ("header_unicode", "TEXT NULL"),
        ("punjabi_ft", "TEXT NULL"),
        ("punjabi_bdb", "TEXT NULL"),
        ("spanish_sn", "TEXT NULL"),
        ("hindi_sts", "TEXT NULL"),
        ("translit_hindi", "TEXT NULL"),
        ("translit_ipa", "TEXT NULL"),
        ("translit_urdu", "TEXT NULL"),
    ]
    for column, ddl in verse_columns:
        if not _column_exists(cursor, "verses", column):
            cursor.execute(f"ALTER TABLE verses ADD COLUMN `{column}` {ddl}")
            print(f"added verses.{column}")
    for column, ddl in search_columns:
        if not _column_exists(cursor, "search_documents", column):
            cursor.execute(f"ALTER TABLE search_documents ADD COLUMN `{column}` {ddl}")
            print(f"added search_documents.{column}")
    indexes = [
        ("verses", "uq_verses_source_index", "UNIQUE KEY uq_verses_source_index (source_code, index_id)"),
        ("verses", "idx_verses_header", "KEY idx_verses_header (header_id)"),
        ("verses", "idx_verses_original_source", "KEY idx_verses_original_source (original_source_id)"),
        ("search_documents", "idx_sd_index", "KEY idx_sd_index (source_code, index_id)"),
        ("search_documents", "idx_sd_original_source", "KEY idx_sd_original_source (original_source_id)"),
    ]
    for table, name, ddl in indexes:
        if not _index_exists(cursor, table, name):
            cursor.execute(f"ALTER TABLE `{table}` ADD {ddl}")
            print(f"added {table}.{name}")
    cursor.close()


def main() -> int:
    admin = None
    try:
        admin = try_connect(APP_USER, APP_PASSWORD, DATABASE)
        print(f"Connected as {APP_USER} to {DATABASE}")
    except mysql.connector.Error as exc:
        print(f"{APP_USER}/{DATABASE} failed: {exc.errno} {exc.msg}")
        try:
            admin = try_connect(APP_USER, APP_PASSWORD)
            print(f"Connected as {APP_USER} without database")
            ensure_database(admin)
        except mysql.connector.Error as app_exc:
            print(f"{APP_USER} without database failed: {app_exc.errno} {app_exc.msg}")
            try:
                admin = try_connect("root", ROOT_PASSWORD)
                print("Connected as root using MYSQL_ROOT_PASSWORD from .env")
                ensure_database(admin)
            except mysql.connector.Error as root_exc:
                print(
                    "Could not connect with .env app user or MYSQL_ROOT_PASSWORD. "
                    f"Root error: {root_exc.errno} {root_exc.msg}"
                )
                return 1

    if admin is None:
        return 1

    if admin.database != DATABASE:
        admin.database = DATABASE

    print(f"Applying {SCHEMA}")
    apply_schema(admin)
    ensure_schema_extras(admin)
    admin.close()

    app = try_connect(APP_USER, APP_PASSWORD, DATABASE)
    cursor = app.cursor()
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.execute(
        "SELECT TABLE_NAME, INDEX_TYPE FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA=%s AND INDEX_TYPE='FULLTEXT'",
        (DATABASE,),
    )
    fulltext = cursor.fetchall()
    cursor.close()
    app.close()
    print("tables:", ", ".join(tables))
    print("fulltext indexes:", fulltext)
    return 0


if __name__ == "__main__":
    sys.exit(main())
