#!/usr/bin/env sh
kubectl port-forward pods/$(kubectl get pods -l krules.airspot.dev/app=django -o jsonpath='{.items[*].metadata.name}')  $1:8080