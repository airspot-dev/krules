FROM rulesset-image-base-setup:latest

RUN pip install krules-env==0.2.6

CMD exec gunicorn --bind :8080 --workers 1 --threads 8 main:app
