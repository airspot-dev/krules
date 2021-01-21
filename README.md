![](.support/krules_ext_logo.png)

KRules is an open source framework that provides, to Python developers, a flexible and fast way to build cloud native applications, 
creating event driven, context aware, and reactive microservices in a Kubernetes cluster.

Extended documentation is not yet available, but you can take a look at [our introductionary material](https://intro.krules.io).

Meanwhile, if you are brave and you do not fear the unknown [get in touch with us](mailto:info@airspot.tech). 

# Repos

## Starting material

- [krules-project-template](https://github.com/airspot-dev/krules-project-template): A KRules empty project sekeleton. Include a a step by step guide.

## Core libraries

- [krules-core](https://github.com/airspot-dev/krules-core): KRules core package containing all base components

- [krules-dispatcher-cloudevents](https://github.com/airspot-dev/krules-dispatcher-cloudevents): KRules's router dispatcher component.
It sends cloudevents via http to a configurable url

- [krules-env](https://github.com/airspot-dev/krules-env): A module mainly intended for the setup of different environments in the context of a basic image

- [krules-controllers](https://github.com/airspot-dev/krules-controllers): Includes rulesets in krules-system namespace

## Subjects storages

- [krules-subjects-redis-storage](https://github.com/airspot-dev/krules-subjects-storage-redis): Redis based subjects storage

- [krules-subjects-storage-mongodb](https://github.com/airspot-dev/krules-subjects-storage-mongodb): MongoDB based subjects storage

- [krules-subjects-storage-k8s](https://github.com/airspot-dev/krules-subjects-storage-k8s): A subjects storage that use Kubernetes resources as subjects storage 

## Miscellaneous

- [rulesset-image-base](https://github.com/airspot-dev/rulesset-image-base): Repo to build the Rulesets Docker image base 

## Code Examples

- [IoT example](https://github.com/airspot-dev/iot-demo)

- [Knative blue-green exemple](https://github.com/airspot-dev/knative-bluegreen-demo)

## License

Each KRules product is released under an Apache License 2.0 license. Refer to [LICENSE](.support/LICENSE) for license text.

