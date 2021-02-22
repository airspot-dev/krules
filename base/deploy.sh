#!/bin/bash

#set -x
if [[ -z "${DOCKER_REGISTRY}" ]]; then
  echo "DOCKER_REGISTRY not set!"
  exit 1
fi
if [[ -z "${NAMESPACE}" ]]; then
  echo "NAMESPACE not set!"
  exit 1
fi
if [[ -z "${KRULES_APPLICATION}" ]]; then
  echo "KRULES_APPLICATION not set!"
  exit 1
fi

TARGET_IMAGE=${DOCKER_REGISTRY}/${KRULES_APPLICATION}-base
docker build -t ${TARGET_IMAGE} $(dirname $0)
docker push ${TARGET_IMAGE}
docker inspect --format='{{index .RepoDigests 0}}' ${TARGET_IMAGE} > .digest
kubectl apply -n ${NAMESPACE} -k $(dirname $0)/k8s/
kubectl create cm config-krules-project -n ${NAMESPACE} --dry-run=client -oyaml | kubectl apply -f -
kubectl patch cm config-krules-project -n ${NAMESPACE} -p "{\"data\": {\"imageBase\": \"$(cat .digest)\"}}"
