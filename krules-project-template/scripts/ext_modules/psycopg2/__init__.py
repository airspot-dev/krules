import logging
import os
import shutil

PSYCOPG_VERSION = "2.8.6"

deploy__extra_commands = [
    ("RUN", f"apk add --no-cache --virtual .build-deps g++ python3-dev postgresql-dev build-base && \
    apk add --no-cache --update python3 libpq && \
    pip install --no-cache-dir psycopg2=={PSYCOPG_VERSION} && \
    apk del .build-deps")
]
