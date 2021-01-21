# Use an official Python runtime as a parent image
FROM python:3.7

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
ADD . /app

RUN pip install pyyaml flask json-logging requests cloudevents==0.3.0 pytz gunicorn krules-env==0.7 krules-subjects-storage-redis==0.7


ENV FLASK_APP /app/main.py
ENV FLASK_ENV production

CMD exec gunicorn --bind :8080 --workers 1 --threads 8 main:app