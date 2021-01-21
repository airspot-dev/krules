TARGET_IMAGE:=ade8850/k8s-subscriber:pre4
NAMESPACE:=blue-green-demo

all: build push resources

resources:
	kubectl apply -n ${NAMESPACE} -f k8s/apiserversource.yaml
	kubectl apply -n ${NAMESPACE} -f k8s/service.yaml

build:
	docker build -t ${TARGET_IMAGE} .

push:
	docker push ${TARGET_IMAGE}
