SHELL=/bin/bash
TARGET_IMAGE:=ade8850/django-bluegreen-demo:pre8
NAMESPACE:=blue-green-demo


all: build push resources


build:
	docker build -t ${TARGET_IMAGE} .

migrate:
	docker run --env-file env ${TARGET_IMAGE} sh -c "python manage.py makemigrations && python manage.py migrate"

shell:
	docker run --env-file env -ti ${TARGET_IMAGE} sh

run:
	docker run --env-file env -p 80:8000 ${TARGET_IMAGE}

cm:
	cat cm_env.template.yaml \
		|sed "s%_DJANGO_ALLOWED_HOSTS_%${DJANGO_ALLOWED_HOSTS}%"\
		|sed "s%_STATIC_ENDPOINT_URL_%${STATIC_ENDPOINT_URL}%"\
		|sed "s%_STATIC_BUCKET_NAME_%${STATIC_BUCKET_NAME}%"\
		|sed "s%_DJANGO_LOGLEVEL_%${DJANGO_LOGLEVEL}%"\
		|sed "s%_DEBUG_%${DEBUG}%"\
		|sed "s%_DATABASE_ENGINE_%${DATABASE_ENGINE}%"\
		>k8s/django-config.yaml

secrets:
	cat secrets.template.yaml \
		|sed "s%_DATABASE_HOST_%${B64_DATABASE_HOST}%"\
		|sed "s%_DATABASE_NAME_%${B64_DATABASE_NAME}%"\
		|sed "s%_DATABASE_PASSWORD_%${B64_DATABASE_PASSWORD}%"\
		|sed "s%_DATABASE_PORT_%${B64_DATABASE_PORT}%"\
		|sed "s%_DATABASE_USERNAME_%${B64_DATABASE_USERNAME}%"\
		|sed "s%_DJANGO_SECRET_KEY_%${B64_DJANGO_SECRET_KEY}%"\
		|sed "s%_STATIC_ACCESS_KEY_ID_%${B64_STATIC_ACCESS_KEY_ID}%"\
		|sed "s%_STATIC_SECRET_KEY_%${B64_STATIC_SECRET_KEY}%"\
		>k8s/django-secrets.yaml

resources: cm secrets
	kubectl apply -n ${NAMESPACE} -k k8s/

push:
	docker push ${TARGET_IMAGE}