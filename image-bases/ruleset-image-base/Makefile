VERSION=`cat VERSION`
NOW=$(shell date +%Y%m%d%H%M%S)
DEV_VERSION=${VERSION}-${NOW}

release: check_env common app/*.py release/Dockerfile
	docker build -t ruleset-image-base:${VERSION} -t ${DOCKER_REGISTRY}/ruleset-image-base:${VERSION} -t ${DOCKER_REGISTRY}/ruleset-image-base:latest public
	docker push ${DOCKER_REGISTRY}/ruleset-image-base:${VERSION} && docker push ${DOCKER_REGISTRY}/ruleset-image-base:latest

develop: check_env check_dev_env common app/*.py release/Dockerfile
	cp -rf ${KRULES_DEV_PACKAGES_DIR} ./develop/.krules-libs/
	docker build -t ruleset-image-base:${DEV_VERSION} -t ${DOCKER_REGISTRY}/ruleset-image-base:${DEV_VERSION} develop && \
	docker push ${DOCKER_REGISTRY}/ruleset-image-base:${DEV_VERSION}
	rm -rf ./develop/.krules-libs

common: Dockerfile
	docker build -t ruleset-image-base-common .

check_env:
ifndef DOCKER_REGISTRY
	$(error DOCKER_REGISTRY is undefined)
endif

check_dev_env:
ifndef KRULES_DEV_PACKAGES_DIR
	$(error KRULES_DEV_PACKAGES_DIR is undefined)
endif
