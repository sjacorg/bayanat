#!/bin/bash

set -eu

echo "Making sure the database is initialized and the admin user is present"

ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD=$ADMIN_PASSWORD

flask create-db
echo "Database is initialized"

flask install --username $ADMIN_USERNAME --password $ADMIN_PASSWORD
echo "The admin user is present"

exec "$@"