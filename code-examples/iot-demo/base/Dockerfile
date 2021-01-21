FROM gcr.io/airspot/ruleset-image-base:0.7

ADD ./app /app

# nice to have an interactive shell
RUN pip install ipython
ADD ipython_config.py /root/.ipython/profile_default/

RUN pip install krules-subjects-storage-redis==0.7
RUN pip install krules-subjects-storage-k8s==0.7.1
RUN apk add libffi-dev
RUN apk add openssl-dev
RUN pip install pusher==3.0.0

