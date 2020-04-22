#!/usr/bin/env bash

set -x

bumpversion --current-version $(cat VERSION) patch VERSION --allow-dirty
VERSION=$(cat VERSION)

# TODO: pip install in Dockerfile
mkdir -p .t_commonlib
rsync -r ../krules-core/krules_core/ .t_commonlib/krules_core
rsync -r ../krules-core/krules_env/ .t_commonlib/krules_env
rsync -r ../krules-dispatcher-cloudevents/krules_cloudevents/ ./.t_commonlib/krules_cloudevents

docker build -t rulesset-image-base:$VERSION -t gcr.io/airspot/rulesset-image-base:$VERSION .

rm -rf ./.t_commonlib/
