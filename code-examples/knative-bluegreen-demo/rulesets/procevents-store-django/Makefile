TARGET_IMAGE:=ade8850/bluegreen-procevents-store-django:pre3
NAMESPACE:=blue-green-demo

all: build push resources

resources:
	kubectl apply -n ${NAMESPACE} -f k8s/service.yaml
	kubectl apply -n ${NAMESPACE} -f k8s/triggers.yaml

build:
	docker build -t ${TARGET_IMAGE} .

push:
	docker push ${TARGET_IMAGE}
