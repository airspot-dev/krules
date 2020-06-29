FROM rulesset-image-base-setup

ADD ./.krules-public /app/.krules-libs

RUN pip install -r /app/.krules-libs/krules-requirements.txt
WORKDIR /app/.krules-libs/krules-core
RUN python setup.py develop --no-deps

WORKDIR /app/.krules-libs/krules-dispatcher-cloudevents
RUN python setup.py develop --no-deps

WORKDIR /app/.krules-libs/krules-env
RUN python setup.py develop --no-deps

CMD exec gunicorn --bind :8080 --workers 1 --threads 8 main:app
