"""HTTP layer for Coffee Menu API."""

import logging
from typing import Optional, Tuple

from flask import Blueprint, Response, jsonify, request

from schemas import validate_create, validate_update
from services import DrinkAlreadyExistsError, DrinkNotFoundError, DrinkService

logger = logging.getLogger(__name__)

JsonResponse = Tuple[Response, int]


def ok(data, code: int = 200) -> JsonResponse:
    return jsonify({"status": "success", "data": data, "error": ""}), code


def fail(message: str, code: int) -> JsonResponse:
    logger.error("HTTP %d — %s", code, message)
    return jsonify({"status": "error", "data": {}, "error": message}), code


def _require_json() -> Optional[dict]:
    """Return parsed JSON body, or None if the request body is not valid JSON."""
    return request.get_json(silent=True)


def register_routes(service: DrinkService) -> Blueprint:
    """Create a fresh Blueprint each call (safe for repeated create_app() in tests)."""
    bp = Blueprint("drinks", __name__, url_prefix="/drinks")

    @bp.get("/")
    def list_drinks():
        return ok(service.get_all())

    @bp.post("/")
    def create_drink():
        body = _require_json()
        if body is None:
            return fail("Request body must be valid JSON", 400)
        schema, error = validate_create(body)
        if error:
            return fail(error, 400)
        try:
            return ok(service.create(schema), 201)
        except DrinkAlreadyExistsError as exc:
            return fail(str(exc), 409)

    @bp.put("/<int:drink_id>")
    def update_drink(drink_id: int):
        body = _require_json()
        if body is None:
            return fail("Request body must be valid JSON", 400)
        schema, error = validate_update(body)
        if error:
            return fail(error, 400)
        try:
            return ok(service.update(drink_id, schema))
        except DrinkNotFoundError as exc:
            return fail(str(exc), 404)

    @bp.delete("/<int:drink_id>")
    def delete_drink(drink_id: int):
        try:
            return ok(service.delete(drink_id))
        except DrinkNotFoundError as exc:
            return fail(str(exc), 404)

    return bp