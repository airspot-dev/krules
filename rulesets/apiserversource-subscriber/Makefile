SHELL=/bin/bash
TARGET_IMAGE:=${DOCKER_REGISTRY}/apiserversource-subscriber
NAMESPACE:=krules-system

all: build push resources

resources:
	kubectl apply -n ${NAMESPACE} -k k8s

build: check-env
	docker build -t ${TARGET_IMAGE} .

push: check-env
	docker push ${TARGET_IMAGE}
	docker inspect --format='{{index .RepoDigests 0}}' ${TARGET_IMAGE} >.digest
	sed -i "s%image: .*%image: $(shell cat .digest)%" k8s/service.yaml

check-env:
ifndef DOCKER_REGISTRY
	$(error DOCKER_REGISTRY is undefined)
endif