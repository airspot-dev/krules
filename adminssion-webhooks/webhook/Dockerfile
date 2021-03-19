FROM alpine:3.11.6
MAINTAINER Airspot <info@airspot.tech>

ADD /app /app

RUN apk add --no-cache --virtual .build-deps g++ python3-dev && \
    apk add --no-cache build-base && \
    apk add --no-cache --update python3 && \
    pip3 install --upgrade pip setuptools && \
    pip3 install --no-cache-dir -r /app/requirements.txt && \
    apk del .build-deps

#RUN pip3 install gunicorn krules-env krules-subjects-storage-redis
## missing from krules-env
#RUN pip3 install pyyaml json_logging flask
## missing from krules-dispatcher
#RUN pip3 install pytz requests


ENV PYTHONPATH /app
ENV FLASK_APP /app/main.py
ENV FLASK_ENV production

CMD exec gunicorn --bind :8080 --workers 1 --threads 8 main:app