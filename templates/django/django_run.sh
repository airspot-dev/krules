#!/bin/sh

python3 manage.py collectstatic --noinput

daphne --port 8080 ${SITE_NAME}.asgi:application