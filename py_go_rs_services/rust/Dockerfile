FROM rust:latest AS builder

WORKDIR /app

# D2: cache dependency compilation separately from application source.
# Create a dummy main so `cargo build --release` can compile all deps
# without any application code — this layer is invalidated only when
# Cargo.toml / Cargo.lock change, not on every src edit.
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo 'fn main(){}' > src/main.rs \
    && cargo build --release \
    && rm -rf src

# Now compile the real source. Only this layer re-runs on src changes.
COPY src ./src
# Touch main.rs so cargo sees it as newer than the cached dep artifacts.
RUN touch src/main.rs && cargo build --release

# ── Runtime ──
FROM debian:bookworm-slim

# Устанавливаем ca-certificates и curl (curl нужен для healthcheck)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/target/release/loyalty-service .

EXPOSE 8081
CMD ["./loyalty-service"]