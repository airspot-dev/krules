#FROM gcr.io/airspot/ruleset-image-base:0.8.5
FROM lorenzocampo/ruleset-image-base:0.8.5-20210311115358

ADD ./app /app

# nice to have an interactive shell
RUN pip install ipython
ADD ipython_config.py /root/.ipython/profile_default/

# RUN pip install krules-subjects-storage-redis==0.8.5
# RUN pip install krules-subjects-storage-mongodb==0.8.5