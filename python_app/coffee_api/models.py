"""Database models and connection management for Coffee Menu API."""

import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS drinks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    description TEXT,
    price       REAL    NOT NULL,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
)
"""


def utc_now() -> str:
    """Return current UTC time as ISO-8601 string (seconds precision)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Drink:
    """In-memory representation of a menu drink row."""

    id: int
    name: str
    price: float
    description: Optional[str]
    created_at: str
    updated_at: str

    def to_dict(self) -> dict:
        # Field order matches dataclass declaration order
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Drink":
        return cls(
            id=row["id"],
            name=row["name"],
            price=row["price"],
            description=row["description"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class Database:
    """Thin sqlite3 wrapper with transactional context manager.

    Supports both file-based paths and the special ":memory:" value.
    When ":memory:" is used, a *single* connection is kept open so that all
    callers share the same in-memory database — matching the behaviour of a
    real file-based DB across multiple connect() calls.
    """

    def __init__(self, db_path: str = "coffee.db") -> None:
        self.db_path = db_path
        self._memory_conn: Optional[sqlite3.Connection] = None
        if db_path == ":memory:":
            self._memory_conn = self._open()
        logger.debug("Database configured: path=%s", db_path)

    def _open(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _transact(self, conn: sqlite3.Connection):
        """Shared commit/rollback logic for any connection."""
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    @contextmanager
    def connect(self):
        """Yield a connection; commit on success, rollback on error."""
        if self._memory_conn is not None:
            with self._transact(self._memory_conn):
                yield self._memory_conn
        else:
            conn = self._open()
            conn.execute("PRAGMA journal_mode=WAL")
            try:
                with self._transact(conn):
                    yield conn
            finally:
                conn.close()

    def init_schema(self) -> None:
        """Idempotently create the drinks table."""
        with self.connect() as conn:
            conn.execute(_CREATE_TABLE_SQL)
        logger.info("Schema ready: path=%s", self.db_path)