FROM rulesset-image-base-setup

ADD ./.krules-libs /krules-libs
ADD ./requirements.txt /krules-libs

RUN pip install -r /krules-libs/requirements.txt
RUN cd /krules-libs/krules-core && python3 setup.py develop
RUN cd /krules-libs/krules-dispatcher-cloudevents && python3 setup.py develop --no-deps
RUN cd /krules-libs/krules-env && python3 setup.py develop --no-deps

CMD exec gunicorn --bind :8080 --workers 1 --threads 8 main:app
