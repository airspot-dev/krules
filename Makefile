VERSION=`cat VERSION`
DEV_VERSION = ${VERSION}-`date +%Y%m%d%H%M%S`

PROJECT=`gcloud config get-value project`

ifndef DOCKER_REGISTRY
	DOCKER_REGISTRY=eu.gcr.io/$(PROJECT)
endif

public: Dockerfile app/*.py public/Dockerfile
	bumpversion --current-version $(cat VERSION) patch VERSION --allow-dirty
	docker build -t rulesset-image-base-setup:$VERSION -t ${DOCKER_REGISTRY}/rulesset-image-base-setup:$VERSION .
	docker build -t rulesset-image-base:$VERSION -t ${DOCKER_REGISTRY}/rulesset-image-base:$VERSION public
	docker push ${DOCKER_REGISTRY}/rulesset-image-base:$VERSION

develop: Dockerfile app/*.py develop/Dockerfile
	VERSION=$(cat VERSION)
	docker build -t rulesset-image-base-setup:$VERSION -t ${DOCKER_REGISTRY}/rulesset-image-base-setup:$VERSION .
	VERSION=
	docker build -t rulesset-image-base:$VERSION -t ${DOCKER_REGISTRY}/rulesset-image-base:$VERSION develop
	docker push ${DOCKER_REGISTRY}/rulesset-image-base:$VERSION

test:
	echo ${DOCKER_REGISTRY}
	echo ${DEV_VERSION}
