release: check_release_env common app/*.py release/Dockerfile
	docker build -t ruleset-image-base:${RELEASE_VERSION} -t ${DOCKER_REGISTRY}/ruleset-image-base:${VERSION} \
	-t ${DOCKER_REGISTRY}/ruleset-image-base:latest public &&
	docker push ${DOCKER_REGISTRY}/ruleset-image-base:${RELEASE_VERSION} && docker push ${DOCKER_REGISTRY}/ruleset-image-base:latest

develop: check_env common app/*.py develop/Dockerfile
	rsync -r ../../libs/* ./develop/.krules-libs/
	docker build -t ${DOCKER_REGISTRY}/ruleset-image-base develop && \
	docker push ${DOCKER_REGISTRY}/ruleset-image-base && \
	docker inspect --format='{{index .RepoDigests 0}}' ${DOCKER_REGISTRY}/ruleset-image-base > .digest
	rm -rf ./develop/.krules-libs

common: Dockerfile
	docker build -t ruleset-image-base-common .

check_env:
ifndef DOCKER_REGISTRY
	$(error DOCKER_REGISTRY is undefined)
endif

check_release_env: check_env
ifndef RELEASE_VERSION
	$(error RELEASE_VERSION is undefined)
endif
