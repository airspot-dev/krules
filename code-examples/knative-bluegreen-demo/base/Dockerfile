FROM gcr.io/airspot/ruleset-image-base:0.4.4

ADD ./app /app

# nice to have an interactive shell
#RUN pip install ipython
#ADD ipython_config.py /root/.ipython/profile_default/
ADD django-requirements.txt /app/django-requirements.txt
RUN apk update
RUN apk add git python3-dev
RUN \
 apk add --no-cache postgresql-libs && \
 apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev
RUN pip install -r /app/django-requirements.txt
RUN apk --purge del .build-deps

RUN pip install krules-subjects-storage-k8s==0.4.43

#RUN pip install pykube-ng==20.7.2

# uncomment for subjects redis support
RUN pip install krules-subjects-storage-redis==0.4.4

