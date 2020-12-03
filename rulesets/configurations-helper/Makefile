SHELL=/bin/bash
TARGET_IMAGE:=${DOCKER_REGISTRY}/configurations-helper
NAMESPACE:=krules-system

all: build push

resources:
	sed -i "s%image: .*%image: $(shell cat .digest)%" k8s/service.yaml
	kubectl apply -n ${NAMESPACE} -k k8s

build: check-env
	docker build -t ${TARGET_IMAGE} .

push: check-env
	docker push ${TARGET_IMAGE}
	docker inspect --format='{{index .RepoDigests 0}}' ${TARGET_IMAGE} >.digest

check-env:
ifndef DOCKER_REGISTRY
	$(error DOCKER_REGISTRY is undefined)
endif