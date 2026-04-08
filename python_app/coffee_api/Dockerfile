# ── Base image ────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# PYTHONUNBUFFERED – logs reach stdout/stderr immediately (no block-buffering).
# PYTHONDONTWRITEBYTECODE – skip .pyc files; keeps the image clean.
# DATABASE_URL – SQLite file lives in a dedicated directory (mountable volume).
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATABASE_URL=/app/data/coffee.db

WORKDIR /app

# ── Dependencies ──────────────────────────────────────────────────────────────
# Copied separately so Docker can cache this layer independently of source changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application source ────────────────────────────────────────────────────────
# Only production modules — tests are excluded via .dockerignore.
COPY app.py models.py routes.py schemas.py services.py ./

# ── Non-root user + data directory ───────────────────────────────────────────
# Running as non-root follows the principle of least privilege.
# /app/data is created here so the volume mount point exists with correct ownership.
RUN adduser --disabled-password --gecos "" appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

USER appuser

# ── Networking ────────────────────────────────────────────────────────────────
EXPOSE 5000

# ── Health check ──────────────────────────────────────────────────────────────
# Uses Python stdlib urllib — curl/wget are absent in slim images.
# --start-period: grace time for Flask to initialise and create the DB schema.
# --interval:     probe cadence after the start period expires.
# --timeout:      per-probe deadline; exceeding it counts as a failure.
# --retries:      consecutive failures needed to mark the container unhealthy.
#
# urlopen raises on connection error or non-2xx → unhandled exception → exit 1.
# On success the process exits normally → exit 0.
# timeout=4 is 1 s under --timeout=5s so Docker's deadline never fires first.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/drinks/', timeout=4)"

CMD ["python", "app.py"]