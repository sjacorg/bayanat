FROM python:3.8.16-slim

MAINTAINER SJAC "tech@syriaaccountability.org"

RUN apt-get update -y && \
    apt-get install -y python-dev apt-utils libjpeg62-turbo-dev libzip-dev libxml2-dev libssl-dev \
    libffi-dev libxslt1-dev  libncurses5-dev python-setuptools libpq-dev git exiftool build-essential

# We copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

ENV FLASK_APP=run.py
ENV C_FORCE_ROOT="true"
ENV SQLALCHEMY_DATABASE_URI="postgresql://enferno:verystrongpass@postgres/enferno"
ENV REDIS_HOSTNAME="redis"
ENV REDIS_PASSWORD="verystrongpass"
ENV REDIS_PORT=6379
ENV REDIS_BROKER_DB=2
ENV REDIS_DB=0
ENV REDIS_RESULT_DB=3
ENV SESSION_DB_REDIS=1

RUN echo 'alias act="source env/bin/activate"' >> ~/.bashrc
RUN echo 'alias ee="export FLASK_APP=run.py && export FLASK_DEBUG=0"' >> ~/.bashrc

CMD [ "uwsgi", "--http", "0.0.0.0:5000", \
               "--protocol", "uwsgi", \
               "--wsgi", "run:app" ]

