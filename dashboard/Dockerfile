# Multi-stage build: compile in a full toolchain image, ship the bare binary.
FROM rust:1.84-slim AS builder
WORKDIR /build
# Cache dependencies first: only recompiles when manifests change.
COPY Cargo.toml Cargo.lock ./
COPY crates/world-feed/Cargo.toml crates/world-feed/Cargo.toml
COPY crates/dashboard-app/Cargo.toml crates/dashboard-app/Cargo.toml
RUN mkdir -p crates/world-feed/src crates/dashboard-app/src \
    && echo "" > crates/world-feed/src/lib.rs \
    && echo "fn main() {}" > crates/dashboard-app/src/main.rs \
    && cargo build --release \
    && rm crates/world-feed/src/lib.rs crates/dashboard-app/src/main.rs
COPY crates crates
RUN touch crates/world-feed/src/lib.rs crates/dashboard-app/src/main.rs \
    && cargo build --release --bin dashboard

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /build/target/release/dashboard /usr/local/bin/dashboard
EXPOSE 8400
ENTRYPOINT ["/usr/local/bin/dashboard"]
