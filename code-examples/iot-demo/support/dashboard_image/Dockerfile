# build stage
#FROM node:lts-alpine as build-stage
#WORKDIR /app
#COPY package*.json ./
#RUN npm install
#COPY . .
#RUN npm run build

FROM alpine:3.11.6
MAINTAINER Airspot <info@airspot.tech>

RUN apk add --no-cache --virtual .build-deps g++ python3-dev && \
    apk add --no-cache build-base && \
    apk add --no-cache --update python3 && \
    pip3 install --upgrade pip setuptools

RUN pip3 install gunicorn flask

ADD . /app

ENV PYTHONPATH /app
ENV FLASK_APP /app/main.py
ENV FLASK_ENV production

CMD exec gunicorn --bind :8080 --workers 1 --threads 8 main:app
