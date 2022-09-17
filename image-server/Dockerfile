FROM lukemathwalker/cargo-chef:latest-rust-1.63 AS chef
WORKDIR app

FROM chef AS planner
COPY . .
RUN cargo chef prepare --recipe-path recipe.json

FROM chef AS builder
COPY --from=planner /app/recipe.json recipe.json
RUN cargo chef cook --release --recipe-path recipe.json

COPY . .
ENV SQLX_OFFLINE true
RUN cargo build --release
RUN ls -lsah target/release

FROM debian:bullseye-slim AS runtime
WORKDIR app

RUN apt-get update -y \
    && apt-get install -y --no-install-recommends ca-certificates libssl-dev \
    # Clean up
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Etc/UTC
ENV RUST_LOG=info,sqlx=warn

COPY --from=builder /app/target/release/image-server /app/image-server
RUN mkdir /app/data

EXPOSE 8000
ENTRYPOINT ["/app/image-server"]
