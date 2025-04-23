# ---- use a base image to compile requirements / save image size -----
FROM ubuntu:24.04 as base
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y && \
    apt-get install -yq python3.12 python3.12-dev python3.12-venv python3-pip \
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
# The `--copies` option tells `venv` to copy libs and binaries
RUN python3.12 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY ./requirements/main.txt  /app/requirements.txt

RUN . /opt/venv/bin/activate

RUN pip install --no-cache-dir -Ur requirements.txt
RUN ls -la /opt/venv/bin/

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
# copy compiled virtualenv
COPY --from=base /opt/venv /opt/venv

COPY --chown=ubuntu:ubuntu ./flask/bin/entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod 550 /usr/local/bin/entrypoint.sh

ENV PATH="/opt/venv/bin:$PATH"

USER ubuntu

CMD ["/usr/local/bin/entrypoint.sh"]
