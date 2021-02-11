# krules-subjects-storage-k8s

[KRules](https://github.com/airspot-dev/krules) is a rules engine primarily intended to run on Kubernetes. 
However the core can be easily used even in different contexts. 
In addition to the core part, you need at least one subject implementation.

This module implements the storage component of the subjects-store based on kubernetes itself

This is not intended for general use but to specifically map kubernetes resources as subjects.
