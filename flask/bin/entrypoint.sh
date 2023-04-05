#!/bin/sh
set -e

if [ "$ROLE" = "flask" ]; then
  flask create-db-exts
  flask create-db
  echo ":: Starting Bayanat ::"
  exec uwsgi --http 0.0.0.0:5000 --protocol uwsgi --master --enable-threads --threads 2  --processes 1 --wsgi run:app

elif [ "$ROLE" = "celery" ]; then
  echo ":: Starting Celery for Bayanat ::"
  exec celery -A enferno.tasks worker --autoscale 1,5 -l error -B -s /tmp/celerybeat-schedule
fi

