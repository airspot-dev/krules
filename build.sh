#!/usr/bin/env bash

set -x

bumpversion --current-version $(cat VERSION) patch VERSION --allow-dirty
VERSION=$(cat VERSION)

docker build -t rulesset-image-base:$VERSION -t ${DOCKER_REGISTRY}/rulesset-image-base:$VERSION .
