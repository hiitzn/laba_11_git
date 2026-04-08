"""Business-logic layer for Coffee Menu API.

DrinkService is the single point of truth for all drink operations.
It receives a Database instance via constructor (Dependency Injection)
and never imports Flask — keeping it fully framework-independent.
"""

import logging
import sqlite3
from typing import List

from models import Database, Drink, utc_now
from schemas import CreateDrinkSchema, UpdateDrinkSchema

logger = logging.getLogger(__name__)


class DrinkNotFoundError(Exception):
    """Raised when a requested drink does not exist."""


class DrinkAlreadyExistsError(Exception):
    """Raised when creating a drink whose name is already taken."""


class DrinkService:
    """All CRUD operations for drinks."""

    def __init__(self, database: Database) -> None:
        self._db = database

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_all(self) -> List[dict]:
        logger.debug("Fetching all drinks")
        with self._db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM drinks ORDER BY created_at DESC"
            ).fetchall()
        drinks = [Drink.from_row(r).to_dict() for r in rows]
        logger.info("Listed %d drink(s)", len(drinks))
        return drinks

    def _get_by_id(self, drink_id: int) -> Drink:
        """Internal helper — fetch one drink or raise DrinkNotFoundError."""
        logger.debug("Fetching drink id=%d", drink_id)
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM drinks WHERE id = ?", (drink_id,)
            ).fetchone()
        if row is None:
            logger.warning("Drink id=%d not found", drink_id)
            raise DrinkNotFoundError(f"Drink with id={drink_id} not found")
        return Drink.from_row(row)

    # ── Commands ──────────────────────────────────────────────────────────────

    def create(self, schema: CreateDrinkSchema) -> dict:
        ts = utc_now()
        try:
            with self._db.connect() as conn:
                cursor = conn.execute(
                    "INSERT INTO drinks (name, description, price, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (schema.name, schema.description, schema.price, ts, ts),
                )
                new_id = cursor.lastrowid
        except sqlite3.IntegrityError as exc:
            logger.warning("Duplicate name='%s'", schema.name)
            raise DrinkAlreadyExistsError(
                f"Drink '{schema.name}' already exists"
            ) from exc

        # Build Drink in-memory — avoids a second SELECT after INSERT
        drink = Drink(
            id=new_id,
            name=schema.name,
            price=schema.price,
            description=schema.description,
            created_at=ts,
            updated_at=ts,
        )
        logger.info("Created drink id=%d name='%s'", drink.id, drink.name)
        return drink.to_dict()

    # NOTE: passing description=None preserves the existing value.
    # To clear a description, the client must pass an empty string
    # (which is normalised to None by the schema).
    def update(self, drink_id: int, schema: UpdateDrinkSchema) -> dict:
        drink = self._get_by_id(drink_id)  # raises DrinkNotFoundError if missing

        new_price = schema.price if schema.price is not None else drink.price
        new_desc = schema.description if schema.description is not None else drink.description
        ts = utc_now()  # captured once so DB row and returned dict are identical

        with self._db.connect() as conn:
            conn.execute(
                "UPDATE drinks SET price = ?, description = ?, updated_at = ? WHERE id = ?",
                (new_price, new_desc, ts, drink_id),
            )

        # Build updated Drink in-memory — avoids a second SELECT after UPDATE
        updated = Drink(
            id=drink.id,
            name=drink.name,
            price=new_price,
            description=new_desc,
            created_at=drink.created_at,
            updated_at=ts,
        )
        logger.info("Updated drink id=%d", drink_id)
        return updated.to_dict()

    def delete(self, drink_id: int) -> dict:
        drink = self._get_by_id(drink_id)  # raises DrinkNotFoundError if missing
        with self._db.connect() as conn:
            conn.execute("DELETE FROM drinks WHERE id = ?", (drink_id,))
        logger.info("Deleted drink id=%d name='%s'", drink_id, drink.name)
        return drink.to_dict()