FROM python:3.7-alpine
MAINTAINER Airspot <info@airspot.tech>
RUN apk add --no-cache --virtual build-dependencies python3 \
    && apk add --virtual build-runtime \
    build-base python3-dev openblas-dev freetype-dev pkgconfig gfortran \
    libffi-dev openssl-dev
RUN apk add  \
    py3-cffi \
    py3-cryptography \
    py3-jinja2 \
    py3-openssl \
    py3-pexpect \
    py3-tornado \
    && ln -s /usr/include/locale.h /usr/include/xlocale.h \
    && python3 -m ensurepip \
    && rm -r /usr/lib/python*/ensurepip \
    && pip3 install --upgrade pip setuptools \
    && ln -sf /usr/bin/python3 /usr/bin/python \
    && ln -sf pip3 /usr/bin/pip \
    && rm -r /root/.cache \
    && apk del build-runtime \
    && apk add --no-cache --virtual build-dependencies $PACKAGES \
    && rm -rf /var/cache/apk/*
RUN apk add --no-cache build-base libffi-dev openssl-dev python-dev curl krb5-dev linux-headers zeromq-dev curl-dev

ENV PYCURL_SSL_LIBRARY=openssl
ENV CPPFLAGS=-I/usr/local/opt/openssl/include
ENV LDFLAGS=-L/usr/local/opt/openssl/lib

RUN apk add --no-cache alpine-sdk \
    && pip install --upgrade pip \
    && pip install pyyaml anyjson wrapt redis rx==1.6.1 dependency-injector \
    pytest jsonpath-rw jsonpath-rw-ext python-dateutil pytz requests gunicorn \
    flask json-logging pycurl krules-env==0.2.2 bumpversion


ADD ./app /app

ENV PYTHONPATH /app
ENV FLASK_APP /app/main.py
ENV FLASK_ENV production

CMD exec gunicorn --bind :8080 --workers 1 --threads 8 main:app
