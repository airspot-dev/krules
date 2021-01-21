FROM alpine:3.11.6
MAINTAINER Airspot <info@airspot.tech>

ADD django-site/requirements.txt /app/requirements.txt

RUN apk add --no-cache --virtual .build-deps g++ python3-dev postgresql-dev build-base && \
    apk add --no-cache --update python3 libpq && \
    python3 -m venv /env && \
    /env/bin/pip3 install --upgrade pip setuptools && \
    /env/bin/pip3 install --no-cache-dir -r /app/requirements.txt && \
    apk del .build-deps


#RUN set -ex \
#    && apk add --no-cache --virtual .build-deps postgresql-dev build-base \
#    && python3 -m venv /env \
#    && /env/bin/pip3 install --upgrade pip \
#    && /env/bin/pip3 install --no-cache-dir -r /app/requirements.txt \
#    && runDeps="$(scanelf --needed --nobanner --recursive /env \
#        | awk '{ gsub(/,/, "\nso:", $2); print "so:" $2 }' \
#        | sort -u \
#        | xargs -r apk info --installed \
#        | sort -u)" \
#    && apk add --virtual rundeps $runDeps \
#    && apk del .build-deps

ADD django-site /app
WORKDIR /app

ENV VIRTUAL_ENV /env
ENV PATH /env/bin:$PATH

RUN python3 manage.py collectstatic

EXPOSE 8000

CMD ["gunicorn", "--bind", ":8080", "--workers", "2", "--threads", "4","mysite.wsgi"]
