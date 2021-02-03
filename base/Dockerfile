FROM gcr.io/airspot/ruleset-image-base:0.8.1

#RUN pip install ipython
#ADD ipython_config.py /root/.ipython/profile_default/
ADD krules-subjects-storage-k8s /krules-subjects-storage-k8s
RUN cd /krules-subjects-storage-k8s && python3 setup.py develop
ADD env.py /app
ADD app_functions /app/app_functions
