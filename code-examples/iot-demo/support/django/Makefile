SHELL=/bin/bash

TARGET_IMAGE:=${DOCKER_REGISTRY}/${KRULES_APPLICATION}-django


all: build push


build: check-env
	docker build --no-cache -t ${TARGET_IMAGE} .

push: check-env
	docker push ${TARGET_IMAGE}
	docker inspect --format='{{index .RepoDigests 0}}' ${TARGET_IMAGE} >.digest


migrate: check-env
	docker run --env-file env ${TARGET_IMAGE} sh -c "python manage.py makemigrations && python manage.py migrate"

shell: check-env
	docker run --env-file env -ti ${TARGET_IMAGE} sh

run: check-env
	docker run --env-file env -p 80:8000 ${TARGET_IMAGE}

update:
	kn service update django --image $(shell cat .digest)

resources: check-env push
	sed -i "s%image: .*%image: $(shell cat .digest)%" k8s/service.yaml
	kubectl apply -n ${NAMESPACE} -k k8s/


check-env:
ifndef DOCKER_REGISTRY
	$(error DOCKER_REGISTRY is not set)
endif
ifndef NAMESPACE
	$(error NAMESPACE is not set)
endif
ifndef KRULES_APPLICATION
	$(error KRULES_APPLICATION is not set)
endif