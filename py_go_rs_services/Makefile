.PHONY: test test-python test-go test-rust up down lint-python

# ── Tests ──────────────────────────────────────────────────────────────────────

test: test-rust test-go test-python

test-python:
	@echo "==> Python tests"
	cd python && pip install -q -r requirements-dev.txt && pytest -v

test-go:
	@echo "==> Go tests"
	cd go && go test ./... -v

test-rust:
	@echo "==> Rust tests"
	cd rust && cargo test

# ── Quality ────────────────────────────────────────────────────────────────────

lint-python:
	@echo "==> Python lint"
	cd python && pip install -q -r requirements-dev.txt && ruff check . && ruff format --check .

# ── Docker ─────────────────────────────────────────────────────────────────────

up:
	docker compose up --build

down:
	docker compose down -v