#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

# If using PostgreSQL, wait until database is ready
if [ "$DATABASE_TYPE" = "postgres" ]; then
    echo "Waiting for postgres database to be ready..."
    python << END
import sys
import time
import psycopg2

while True:
    try:
        psycopg2.connect(
            dbname="${POSTGRES_DB}",
            user="${POSTGRES_USER}",
            password="${POSTGRES_PASSWORD}",
            host="${POSTGRES_HOST}",
            port="${POSTGRES_PORT}"
        )
        break
    except psycopg2.OperationalError as e:
        print("Database not ready yet, retrying in 1 second...")
        time.sleep(1)
END
    echo "PostgreSQL is ready!"
fi

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start server
# By default, run Gunicorn for production-ready serving, but allow override
if [ "$DEBUG" = "True" ] || [ "$DEBUG" = "true" ]; then
    echo "Starting development server..."
    exec python manage.py runserver 0.0.0.0:8000
else
    echo "Starting Gunicorn server..."
    exec gunicorn visulara.wsgi:application --bind 0.0.0.0:8000 --workers 3
fi
