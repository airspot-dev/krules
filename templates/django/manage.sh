#!/bin/sh
kubectl run --rm -ti django-manage --image $(cat .digest) \
  -l krules.airspot.dev/app=django,krules.airspot.dev/type=generic,configs.krules.airspot.dev/django-orm=inject \
   -- python3 /app/manage.py $@