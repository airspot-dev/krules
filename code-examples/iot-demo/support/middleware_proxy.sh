kn service update $1 --min-scale 1
kubectl port-forward \
$(kubectl get pods \
--selector=serving.knative.dev/service=$1 --output=jsonpath="{.items[0].metadata.name}") \
8001:8080