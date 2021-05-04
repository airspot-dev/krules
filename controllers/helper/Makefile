SHELL=/bin/bash
SERVICE_NAME=krules-helper
NAMESPACE=krules-system-dev
WORKING_TARGET_IMAGE:=${DOCKER_REGISTRY}/${SERVICE_NAME}
BASE_RELEASE_TARGET_IMAGE=gcr.io/airspot/${SERVICE_NAME}
RELEASE_TARGET_IMAGE_VERSION=0.9
RELEASE_TARGET_IMAGE:=${BASE_RELEASE_TARGET_IMAGE}:${RELEASE_TARGET_IMAGE_VERSION}

all: build push

service:
	jinja2 \
		-D name=${SERVICE_NAME} \
		-D namespace=${NAMESPACE} \
		-D digest=$(shell cat .digest) \
		k8s/service.yaml.j2  -o k8s/service.yaml
	kubectl apply -f k8s/service.yaml

build: check-env
	rm -rf .common
	rsync -rv ../common/ .common/
	docker build -t ${WORKING_TARGET_IMAGE} .


push: check-env
	docker push ${WORKING_TARGET_IMAGE}
	docker inspect --format='{{index .RepoDigests 0}}' ${WORKING_TARGET_IMAGE} >.digest

release: build
	# webhook
	docker tag ${WORKING_TARGET_IMAGE} ${RELEASE_TARGET_IMAGE}
	docker tag ${RELEASE_TARGET_IMAGE} ${BASE_RELEASE_TARGET_IMAGE}:latest
	docker push ${RELEASE_TARGET_IMAGE}
	docker push ${BASE_RELEASE_TARGET_IMAGE}:latest

check-env:
ifndef DOCKER_REGISTRY
	$(error DOCKER_REGISTRY is undefined)
endif