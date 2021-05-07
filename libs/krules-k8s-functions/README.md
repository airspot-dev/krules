# k8s-functions

KRules is a rules engine primarily intended to run on Kubernetes. 
However, its core can be easily used even in different contexts. 
In addition to the core part, you need at least one subject implementation.

This module implements the storage component of the subjects-store based on kubernetes itself

This is not intended for general use but to specifically map kubernetes resources as subjects.
