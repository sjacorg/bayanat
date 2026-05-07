# ---- builder stage: compile python deps with uv -----------------
FROM ghcr.io/astral-sh/uv:0.5.11-python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_NO_DEV=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Build-time headers only; runtime libs installed in the final stage.
# libimage-exiftool-perl is needed at build time because pyexifinfo's
# setup.py probes for the exiftool binary during wheel install.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    zlib1g-dev \
    libopenjp2-7-dev \
    libimage-exiftool-perl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-install-project

# ---- runtime stage -----------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    XDG_CACHE_HOME=/tmp/.cache

ARG ROLE
ENV ROLE=${ROLE}

# Shared runtime libs: psycopg2 (libpq5), weasyprint (pango/cairo/harfbuzz),
# pillow (libjpeg, libopenjp2), lxml (libxml2, libxslt).
# Celery roles also need exiftool + ffmpeg for media processing.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libcairo2 \
    libxml2 \
    libxslt1.1 \
    libjpeg62-turbo \
    libopenjp2-7 \
    zlib1g \
    libffi8 \
    fonts-dejavu-core \
    && if [ "$ROLE" = "celery" ] || [ "$ROLE" = "celery-ocr" ]; then \
         apt-get install -y --no-install-recommends \
           libimage-exiftool-perl \
           ffmpeg; \
       fi \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN useradd --system --create-home --uid 1000 ubuntu

COPY --chown=ubuntu:ubuntu . /app
COPY --from=builder --chown=ubuntu:ubuntu /app/.venv /app/.venv

COPY --chown=ubuntu:ubuntu ./flask/bin/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 550 /usr/local/bin/entrypoint.sh

USER ubuntu

CMD ["/usr/local/bin/entrypoint.sh"]
