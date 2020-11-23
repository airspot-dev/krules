FROM ruleset-image-base-setup

RUN pip install krules-env==0.6

CMD exec gunicorn --bind :8080 --workers 1 --threads 8 main:app
