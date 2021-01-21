![](.support/krules_ext_logo.png)

KRules is an open source framework that provides, to Python developers, a flexible and fast way to build cloud native applications, 
creating event driven, context aware, and reactive microservices in a Kubernetes cluster.

# Overviews

- [Technical Overview](https://intro.krules.io/OVERVIEW.html): An introductory guide to the framework basic concepts.

- [How argument are processed](https://intro.krules.io/ArgumentProcessors.html): A brief explanation of how argument processing works and 
how it can help application development.

**Base functions library**

Provides a set of basic building blocks to compose your rulesets which will define your microservices-based event-driven application logic.

- [Filters](https://intro.krules.io/Filters.html): A set o basic functions designed to be used in the **filters** section for the purpose of 
define conditions to enable or disable application logic.

- [Processing](https://intro.krules.io/Processing.html): A set o basic functions designed to be used in the **processing** section for the purpose 
of to read and manipulate event data and implement yur application logic.

- [Miscellaneous](https://intro.krules.io/Miscellaneous.html): Generic functions which could be used both like filters or processing.


# Repos

## Core libraries

- [krules-core](https://github.com/airspot-dev/krules-core): KRules core package containing all base components

- [krules-dispatcher-cloudevents](https://github.com/airspot-dev/krules-dispatcher-cloudevents): KRules's router dispatcher component.
It sends cloudevents via http to a configurable url

- [krules-env](https://github.com/airspot-dev/krules-env): A module mainly intended for the setup of different environments in the context of a basic image

## Docker images

- [rulesset-image-base](https://github.com/airspot-dev/rulesset-image-base): Repo to build the Rulesets Docker image base 

## Subjects storages

- [krules-subjects-redis-storage](https://github.com/airspot-dev/krules-subjects-storage-redis): Redis based subjects storage

- [krules-subjects-storage-mongodb](https://github.com/airspot-dev/krules-subjects-storage-mongodb): MongoDB based subjects storage

- [krules-subjects-storage-k8s](https://github.com/airspot-dev/krules-subjects-storage-k8s): A subjects storage that use Kubernetes resources as subjects storage 

## Developer tools

- [krules-project-template](https://github.com/airspot-dev/krules-project-template): A KRules empty project sekeleton. Include a a step by step guide.

## Demos

- [IoT](https://github.com/airspot-dev/iot-demo)

- [Knative blue-green demo](https://github.com/airspot-dev/knative-bluegreen-demo)

## License

Each KRules product is released under an Apache License 2.0 license. Refer to [LICENSE](.support/LICENSE) for license text.

