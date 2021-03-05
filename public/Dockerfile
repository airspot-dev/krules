FROM ruleset-image-base-setup

RUN pip install krules-flask-env==0.8.3.1
RUN pip install krules-subjects-storage-k8s==0.8.3

CMD exec gunicorn --bind :8080 --workers 1 --threads 8 main:app
