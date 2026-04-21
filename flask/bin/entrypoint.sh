#!/bin/sh
set -e

if [ "$ROLE" = "flask" ]; then
  if [ -z "$(flask db current 2>/dev/null | grep -oE '[0-9a-f]{12}')" ]; then
    echo ":: Fresh DB, creating schema ::"
    flask create-db --create-exts
    flask db stamp head
  else
    echo ":: Existing DB, running migrations ::"
    flask db upgrade
  fi
  echo ":: Starting Bayanat ::"
  exec uwsgi --http 0.0.0.0:5000 --protocol uwsgi --master --processes 1 --wsgi run:app

elif [ "$ROLE" = "celery" ]; then
  echo ":: Starting Celery for Bayanat ::"
  exec celery -A enferno.tasks worker --autoscale 3,1 -l error -B -s /tmp/celerybeat-schedule

elif [ "$ROLE" = "celery-ocr" ]; then
  echo ":: Starting Celery OCR Worker for Bayanat ::"
  exec celery -A enferno.tasks worker -Q ocr --autoscale 10,3 -l error -n ocr@%h
fi

