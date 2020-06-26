FROM rulesset-image-base-setup

ADD ${KRULES_DEV_PACKAGES_DIR} /app/

CMD exec gunicorn --bind :8080 --workers 1 --threads 8 main:app
