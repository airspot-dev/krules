FROM rulesset-image-base-setup

ADD ./.krules-libs /krules-libs

RUN pip install -r /krules-libs/krules-requirements.txt
RUN cd /krules-libs/krules-core && python setup.py develop --no-deps
RUN cd /krules-libs/krules-dispatcher-cloudevents && python setup.py develop --no-deps
RUN cd /krules-libs/krules-env && python setup.py develop --no-deps

CMD exec gunicorn --bind :8080 --workers 1 --threads 8 main:app
