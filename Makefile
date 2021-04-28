test: test_core test_dispatcher test_env test_flask_env test_k8s test_provider_redis test_provider_mongodb

test_core:
	cd ./libs/krules-core && make test

test_dispatcher:
	cd ./libs/krules-dispatcher-cloudevents && make test

test_env:
	cd ./libs/krules-env && make test

test_flask_env:
	cd ./libs/krules-env && make test

test_k8s:
	cd ./libs/k8s-functions && make test

test_provider_redis:
	cd ./subjects-storage-providers/redis && make test

test_provider_mongodb:
	cd ./subjects-storage-providers/mongodb && make test