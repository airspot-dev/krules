FROM ruleset-image-base-setup

RUN pip install krules-env==0.9
RUN pip install krules-subjects-storage-k8s==0.9

CMD exec gunicorn --bind :8080 --workers 1 --threads 8 main:app
