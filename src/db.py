from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import mysql.connector
from mysql.connector.connection import MySQLConnection

from .config import get_settings


def get_connection() -> MySQLConnection:
    settings = get_settings()
    return mysql.connector.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
        charset="utf8mb4",
        collation="utf8mb4_0900_ai_ci",
        autocommit=False,
        use_unicode=True,
    )


@contextmanager
def db_cursor(commit: bool = False) -> Iterator:
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        yield cursor
        if commit:
            connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
