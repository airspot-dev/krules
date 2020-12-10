FROM gcr.io/airspot/ruleset-image-base:0.7

RUN pip install ipython
ADD ipython_config.py /root/.ipython/profile_default/
ADD krules-subjects-storage-k8s /krules-subjects-storage-k8s
RUN cd /krules-subjects-storage-k8s && python3 setup.py develop
#ADD krules-core /krules-core
#RUN cd /krules-core && python3 setup.py develop
#ENV PYTHONPATH=/krules-core:/app
ADD env.py /app
ADD app_functions /app/app_functions
#RUN pip install krules-subjects-storage-k8s==0.7.1