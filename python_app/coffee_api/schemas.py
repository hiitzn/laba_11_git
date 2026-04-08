"""Request payload validation for Coffee Menu API.

Each public function returns (schema | None, error_message | None).
Only one of the two values is non-None at a time.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

# Maximum allowed lengths
_MAX_NAME_LEN = 100
_MAX_DESC_LEN = 500


@dataclass(frozen=True)
class CreateDrinkSchema:
    name: str
    price: float
    description: Optional[str] = None


@dataclass(frozen=True)
class UpdateDrinkSchema:
    price: Optional[float] = None
    description: Optional[str] = None


# ── Private helpers ───────────────────────────────────────────────────────────

def _check_price(value) -> Optional[str]:
    """Return an error string if *value* is not a valid price, else None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "Field 'price' must be a number"
    if value <= 0:
        return "Field 'price' must be greater than 0"
    return None


def _check_description(value) -> Optional[str]:
    """Return an error string if *value* is not a valid description, else None."""
    if value is None:
        return None
    if not isinstance(value, str):
        return "Field 'description' must be a string"
    if len(value) > _MAX_DESC_LEN:
        return f"Field 'description' must be at most {_MAX_DESC_LEN} characters"
    return None


def _sanitise_description(value: Optional[str]) -> Optional[str]:
    """Strip whitespace; treat blank strings as absent (None)."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


# ── Public validators ─────────────────────────────────────────────────────────

def validate_create(data: dict) -> Tuple[Optional[CreateDrinkSchema], Optional[str]]:
    """Validate a drink-creation payload."""
    raw_name = data.get("name", "")
    if not isinstance(raw_name, str) or not raw_name.strip():
        return None, "Field 'name' is required and cannot be empty"
    name = raw_name.strip()  # strip once; reused for length check and schema
    if len(name) > _MAX_NAME_LEN:
        return None, f"Field 'name' must be at most {_MAX_NAME_LEN} characters"

    if "price" not in data:
        return None, "Field 'price' is required"
    if (err := _check_price(data["price"])):
        return None, err

    if (err := _check_description(data.get("description"))):
        return None, err

    return CreateDrinkSchema(
        name=name,
        price=float(data["price"]),
        description=_sanitise_description(data.get("description")),
    ), None


def validate_update(data: dict) -> Tuple[Optional[UpdateDrinkSchema], Optional[str]]:
    """Validate a drink-update payload (at least one field required)."""
    if not isinstance(data, dict) or ("price" not in data and "description" not in data):
        return None, "Request body must contain at least 'price' or 'description'"

    price: Optional[float] = None
    if "price" in data:
        if (err := _check_price(data["price"])):
            return None, err
        price = float(data["price"])

    description: Optional[str] = data.get("description")  # may be None (explicit clear)
    if (err := _check_description(description)):
        return None, err

    return UpdateDrinkSchema(
        price=price,
        description=_sanitise_description(description),
    ), None