# KRules : Be serverless

![Krules Logo](https://github.com/airspot-dev/krules/blob/feature/docs/.support/krules_ext_logo.png)

Welcome to this wiki,

in here you can find everything about the KRules framework and its core features.

You will even learn how to build our own rules and integrate them to build a truly serverless environment. 

> **Want to start using it now? go [here](./getting-started.md)**
>
> **Want an environment reference? go [here](./krules-environment.md)**

## What is KRules?

[KRules](https://intro.krules.com) is an open source framework that provides, to Python developers, a flexible and fast way to build cloud native applications, creating event driven, context aware, and reactive microservices in a Kubernetes cluster.

KRules adopts a rules-based approach based on paradigm events-condtions-actions and is inspired by [***the reactive manifesto***](https://www.reactivemanifesto.org) taking full advantages of the Kubernetes cluster and, in particular, the [***Knative eventing***](https://knative.dev/docs).

With Krules you can base your development with a new set of paradigmas:

- **RESPONSIVENESS**: The system responds in a timely manner if at all possible;
- **RESILIENCY**: The system stays responsive in the face of failure;
- **HIGH WORKLOAD TOLERANCE**: The system stays responsive under varying workload;
- **EVENT DRIVEN FLOW**: The system relies on asynchronous event-dispatching to establish a boundary between components that ensure loose coupling, isolation and location transparency.

Please refer to the sections to learn about [***Concepts and Jargon***](./concepts) of the framework, as well to [***get started***](./getting-started) and [***roll your first KRules-based cluster***](./getting-started#cluster-setup).

Before diving into the basics, let us share with you the minimal requirements to run the whole environment.

## Minimal requirements

To run KRules, you need to have a working [Python](https://python.org) environment. We support versions from `Python 3.8.x`.

You will also need `pip` to install all the required packages.

### Preferred IDE

To use KRules smoothly we advise to develop using PyCharm IDE:
it is not a requirement, but if you plan to extend the framework functionality it is the choice we use internally, so we can help you best.
