import os

MENU: dict[str, float] = {
    "espresso": 2.50,
    "latte": 4.00,
    "cappuccino": 3.50,
}

ORDER_SERVICE_URL: str = os.getenv("ORDER_SERVICE_URL", "http://localhost:8080")
HTTP_TIMEOUT: float = float(os.getenv("HTTP_TIMEOUT", "10.0"))

# Built once at import time — reused in every error message.
_AVAILABLE: str = ", ".join(MENU.keys())


def get_price(item: str) -> float:
    """Return the price for *item*.

    Raises:
        ValueError: listing available items without echoing the caller's input,
                    which avoids leaking untrusted data into error responses.
    """
    if item not in MENU:
        raise ValueError(f"Unknown item. Available: {_AVAILABLE}")
    return MENU[item]