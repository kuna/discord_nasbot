# syntax=docker/dockerfile:1

##############################################
# Stage 1: fetch the SpoofDPI release binary
##############################################
FROM debian:bookworm-slim AS spoofdpi

# https://github.com/xvzc/SpoofDPI/releases
ARG SPOOFDPI_VERSION=1.5.3
ARG TARGETARCH

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /out
RUN set -eux; \
    case "${TARGETARCH}" in \
        amd64)   asset="linux_x86_64" ;; \
        arm64)   asset="linux_arm64"  ;; \
        arm)     asset="linux_arm"    ;; \
        386)     asset="linux_i386"   ;; \
        riscv64) asset="linux_riscv64" ;; \
        *) echo "unsupported architecture: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    base="https://github.com/xvzc/SpoofDPI/releases/download/v${SPOOFDPI_VERSION}"; \
    file="spoofdpi_${SPOOFDPI_VERSION}_${asset}.tar.gz"; \
    curl -fsSL -O "${base}/${file}"; \
    curl -fsSL -O "${base}/checksums.txt"; \
    sha256sum --check --ignore-missing checksums.txt; \
    tar -xzf "${file}" spoofdpi; \
    chmod +x spoofdpi; \
    rm -f "${file}" checksums.txt

##############################################
# Stage 2: the bot itself
##############################################
FROM python:3.13-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.12.0 /uv /bin/uv

# tini (-g) forwards signals to the whole process group, so stopping the
# container stops both the bot and spoofdpi
RUN apt-get update \
    && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/*

COPY --from=spoofdpi /out/spoofdpi /usr/local/bin/spoofdpi

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

WORKDIR /app

# dependencies first so source edits don't invalidate the layer
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY . .

# downloads land on a volume; the entrypoint points PROXY_HOST/PROXY_PORT at the
# bundled proxy, so setting them yourself means "use that proxy instead"
ENV DOWNLOAD_FOLDER=/data/downloads \
    SPOOFDPI_ENABLED=1 \
    SPOOFDPI_LISTEN_ADDR=127.0.0.1:8080 \
    SPOOFDPI_DNS_MODE=https \
    SPOOFDPI_DNS_HTTPS_URL=https://1.1.1.1/dns-query \
    SPOOFDPI_LOG_LEVEL=info

RUN useradd --create-home --uid 1000 nasbot \
    && mkdir -p /data/downloads \
    && chown -R nasbot:nasbot /app /data
USER nasbot

VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python docker/healthcheck.py

ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/app/docker/entrypoint.sh"]
CMD ["python", "main.py"]
