SHELL=/bin/bash
TARGET_IMAGE:=ade8850/blue-green-demo-base:pre11
NAMESPACE:=blue-green-demo

all: build push resources

build:
	docker build -t ${TARGET_IMAGE} .

resources:
	kubectl apply -n ${NAMESPACE} -k k8s/

push:
	docker push ${TARGET_IMAGE}