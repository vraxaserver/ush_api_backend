#!/bin/bash
set -e

# Wait for database to be ready (if DB_HOST is set)
if [ -n "$DB_HOST" ]; then
    echo "Waiting for database at ${DB_HOST}:${DB_PORT:-5432}..."
    while ! nc -z ${DB_HOST} ${DB_PORT:-5432} 2>/dev/null; do
        echo "Database is not ready yet..."
        sleep 2
    done
    echo "Database is ready!"
fi

# Wait for Redis to be ready
echo "Waiting for Redis..."
while ! nc -z redis 6379 2>/dev/null; do
    sleep 1
done
echo "Redis is ready!"

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Setup groups (if needed)
echo "Setting up groups..."
python manage.py setup_groups || true

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Execute the command passed to the script
exec "$@"
