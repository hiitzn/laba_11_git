"""Application factory and entry point for Coffee Menu API."""

import logging
import logging.config
import os
from typing import Optional

from flask import Flask

from models import Database
from routes import register_routes
from services import DrinkService

_LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "DEBUG",
        }
    },
    "root": {"handlers": ["console"], "level": "DEBUG"},
}

# Configure logging once at import time — not on every create_app() call,
# which would reconfigure handlers repeatedly during tests.
logging.config.dictConfig(_LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def create_app(config: Optional[dict] = None) -> Flask:
    """Create, configure, and return the Flask application.

    Args:
        config: Optional dict merged into ``app.config`` (useful in tests).
                Recognised keys: ``DATABASE_URL``, ``TESTING``.
    """
    app = Flask(__name__)

    # Set defaults and apply caller overrides in one step
    app.config.update(
        DATABASE_URL=os.getenv("DATABASE_URL", "coffee.db"),
        TESTING=False,
    )
    if config:
        app.config.update(config)

    # Dependency Injection: wire database → service → routes
    database = Database(app.config["DATABASE_URL"])
    database.init_schema()

    service = DrinkService(database)
    app.register_blueprint(register_routes(service))

    logger.info("Coffee Menu API ready (db=%s)", app.config["DATABASE_URL"])
    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000)