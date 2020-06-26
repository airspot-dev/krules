VERSION=`cat VERSION`
NOW=$(shell date +%Y%m%d%H%M%S)
DEV_VERSION=${VERSION}-${NOW}

public: Dockerfile app/*.py public/Dockerfile
	bumpversion --current-version ${VERSION} patch VERSION --allow-dirty
	docker build -t rulesset-image-base-setup .
	docker build -t rulesset-image-base:${VERSION} -t ${DOCKER_REGISTRY}/rulesset-image-base:${VERSION} public
	docker push ${DOCKER_REGISTRY}/rulesset-image-base:${VERSION}

develop: Dockerfile app/*.py develop/Dockerfile
	docker build -t rulesset-image-base-setup . && \
	docker build -t rulesset-image-base:${DEV_VERSION} -t ${DOCKER_REGISTRY}/rulesset-image-base:${DEV_VERSION} develop && \
	docker push ${DOCKER_REGISTRY}/rulesset-image-base:${DEV_VERSION}

ifndef DOCKER_REGISTRY
	$(error DOCKER_REGISTRY is undefined)
endif