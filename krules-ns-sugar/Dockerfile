FROM gcr.io/airspot/ruleset-image-base:0.4.4

ADD rules.py /app

RUN pip install pykube-ng
RUN pip install krules-subjects-storage-k8s==0.4.43