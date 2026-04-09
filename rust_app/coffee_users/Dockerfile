# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM rust:1.75-slim AS builder

WORKDIR /app

# Системные зависимости для rusqlite (bundled feature компилирует SQLite из исходников,
# но libsqlite3-dev нужен на случай динамической линковки и для pkg-config)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlite3-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# ── Кэширование зависимостей ──────────────────────────────────────────────────
# Копируем только манифест и создаём пустой main.rs,
# чтобы слой с cargo build --release пересобирался только при изменении зависимостей.
COPY Cargo.toml .
RUN mkdir src && echo 'fn main() {}' > src/main.rs

RUN cargo build --release && rm -rf src

# ── Сборка реального кода ─────────────────────────────────────────────────────
COPY src/ src/

# touch — сбрасываем mtime, иначе Cargo не увидит изменений поверх кэшированного build
RUN touch src/main.rs && cargo build --release

# ── Stage 2: runner ───────────────────────────────────────────────────────────
FROM debian:bookworm-slim AS runner

WORKDIR /app

# libsqlite3-0 — runtime-библиотека SQLite; curl — для HEALTHCHECK
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlite3-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Директория для файла БД (монтируется как volume в продакшене)
RUN mkdir -p /app/data

# Копируем скомпилированный бинарник из builder
COPY --from=builder /app/target/release/coffee_shop /app/coffee_shop

# БД хранится отдельно от бинарника — удобно для volume-mount
ENV DATABASE_URL=/app/data/coffee_shop.db

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/visitors || exit 1

CMD ["/app/coffee_shop"]