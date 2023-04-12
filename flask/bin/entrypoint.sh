#!/bin/sh
set -e

ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD=$ADMIN_PASSWORD

if [ "$ROLE" = "flask" ]; then
  echo ":: Creating Bayanat Database ::"
  flask create-db-exts
  flask create-db
  echo ":: Trying to Create Admin User ::"
  flask install --username ${ADMIN_USERNAME:-postgres} --password ${ADMIN_PASSWORD:-change_this_password}
  echo ":: Starting Bayanat ::"
  exec uwsgi --http 0.0.0.0:5000 --protocol uwsgi --master --enable-threads --threads 2  --processes 1 --wsgi run:app

elif [ "$ROLE" = "celery" ]; then
  echo ":: Starting Celery for Bayanat ::"
  exec celery -A enferno.tasks worker --autoscale 1,5 -l error -B -s /tmp/celerybeat-schedule
fi

