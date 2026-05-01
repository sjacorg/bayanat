#!/bin/sh
set -e

if [ "$ROLE" = "flask" ]; then
  if [ -z "$(flask db current 2>/dev/null | grep -oE '[0-9a-f]{12}')" ]; then
    echo ":: Fresh DB, creating schema ::"
    flask create-db --create-exts
    flask db stamp head
    # BAY-01-005: bootstrap admin out-of-band (no network-reachable
    # /api/create-admin route exists). On a fresh DB the wizard would
    # otherwise be unreachable. flask install with --username and no
    # --password generates a random password and prints it to stdout;
    # operator retrieves it via `docker-compose logs flask`.
    echo ":: Bootstrapping initial admin user ::"
    flask install --username admin
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

