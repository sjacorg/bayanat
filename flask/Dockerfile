# ---- use a base image to compile requirements / save image size -----
FROM ubuntu:24.04 as base
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y && \
    apt-get install -yq python3.12 python3.12-dev python3.12-venv python3-pip curl git \
    libjpeg8-dev libzip-dev libxml2-dev libssl-dev libffi-dev libxslt1-dev \
    libmysqlclient-dev libncurses5-dev libpq-dev \
    libimage-exiftool-perl

WORKDIR /app

# Sets utf-8 encoding for Python
ENV LANG=C.UTF-8
# Turns off writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# Seems to speed things up
ENV PYTHONUNBUFFERED=1
# Install UV
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml uv.lock /app/

RUN uv sync --frozen --no-install-project

# ----------------- main container -------------------------

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ARG ROLE
ENV ROLE=${ROLE}
RUN echo "Building ${ROLE} container."
RUN if [ "$ROLE" = "flask" ]; then \
    apt-get update -y && apt-get install -yq python3.12 python3.12-dev python3.12-venv \
    postgis libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0 libffi-dev \
    libjpeg-dev libopenjp2-7-dev; \
    elif [ "$ROLE" = "celery" ]; then \
    apt-get update -y && apt-get install -yq python3.12 python3.12-dev python3.12-venv \
    postgis libimage-exiftool-perl ffmpeg libpango-1.0-0 libharfbuzz0b \
    libpangoft2-1.0-0 libffi-dev libjpeg-dev libopenjp2-7-dev; \
    fi
RUN apt clean
RUN apt autoremove

WORKDIR /app

# Sets utf-8 encoding for Python
ENV LANG=C.UTF-8
# Turns off writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# Seems to speed things up
ENV PYTHONUNBUFFERED=1

COPY --chown=ubuntu:ubuntu . /app
# copy UV-built virtualenv
COPY --from=base /app/.venv /app/.venv

COPY --chown=ubuntu:ubuntu ./flask/bin/entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod 550 /usr/local/bin/entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH"

USER ubuntu

CMD ["/usr/local/bin/entrypoint.sh"]
