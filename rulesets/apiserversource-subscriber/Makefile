SHELL=/bin/bash
WORKING_TARGET_IMAGE:=${DOCKER_REGISTRY}/apiserversource-subscriber
NAMESPACE:=krules-system
BASE_RELEASE_TARGET_IMAGE=gcr.io/airspot/apiserversource-subscriber
RELEASE_TARGET_IMAGE_VERSION=0.8.1
RELEASE_TARGET_IMAGE:=${BASE_RELEASE_TARGET_IMAGE}:${RELEASE_TARGET_IMAGE_VERSION}


all: build push

resources:
	sed -i "s%image: .*%image: $(shell cat .digest)%" k8s/service.yaml
	kubectl apply -n ${NAMESPACE} -k k8s

build: check-env
	docker build -t ${WORKING_TARGET_IMAGE} .

push: check-env
	docker push ${WORKING_TARGET_IMAGE}
	docker inspect --format='{{index .RepoDigests 0}}' ${WORKING_TARGET_IMAGE} >.digest

release: build
	docker tag ${WORKING_TARGET_IMAGE} ${RELEASE_TARGET_IMAGE}
	docker tag ${RELEASE_TARGET_IMAGE} ${BASE_RELEASE_TARGET_IMAGE}:latest
	sed -i "s%image: .*%image: ${RELEASE_TARGET_IMAGE}%" k8s/service.yaml
	docker push ${RELEASE_TARGET_IMAGE}
	docker push ${BASE_RELEASE_TARGET_IMAGE}:latest


check-env:
ifndef DOCKER_REGISTRY
	$(error DOCKER_REGISTRY is undefined)
endif