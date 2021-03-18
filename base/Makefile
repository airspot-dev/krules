WORKING_TARGET_IMAGE:=${DOCKER_REGISTRY}/krules-system-base
NAMESPACE:=krules-system
BASE_RELEASE_TARGET_IMAGE=gcr.io/airspot/krules-system-base
RELEASE_TARGET_IMAGE_VERSION=0.8.2
RELEASE_TARGET_IMAGE:=${BASE_RELEASE_TARGET_IMAGE}:${RELEASE_TARGET_IMAGE_VERSION}

all: build push resources

resources:
	kubectl apply -n ${NAMESPACE} -k k8s/

build: check-env
	docker build -t ${WORKING_TARGET_IMAGE} .

push: check-env
	docker push ${WORKING_TARGET_IMAGE}
	docker inspect --format='{{index .RepoDigests 0}}' ${WORKING_TARGET_IMAGE} >.digest

release: build
	docker tag ${WORKING_TARGET_IMAGE} ${RELEASE_TARGET_IMAGE}
	docker tag ${RELEASE_TARGET_IMAGE} ${BASE_RELEASE_TARGET_IMAGE}:latest
	docker push ${RELEASE_TARGET_IMAGE}
	docker push ${BASE_RELEASE_TARGET_IMAGE}:latest

check-env:
ifndef DOCKER_REGISTRY
	$(error DOCKER_REGISTRY is undefined)
endif

