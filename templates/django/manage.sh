#!/bin/sh
kubectl run --rm -ti django-manage --image $(cat .build/.digest) \
  -l krules.dev/app=django,krules.dev/type=generic,config.krules.dev/django-orm=inject \
   -- python3 /app/manage.py $@