#!/bin/bash

set -e

# python manage.py dumpdata accounts.User auth.Group auth.Permission --indent 4 > data/users_data.json
# python manage.py dumpdata spacenter --indent 4 > data/spacenter.json

echo "Loading users data..."
python manage.py loaddata data/users_data.json

echo "Loading spacenter data..."
python manage.py loaddata data/spacenter.json

echo "All data loaded successfully."
