kn service update $1-dashboard --min-scale 1
kubectl port-forward \
$(kubectl get pods \
--selector=serving.knative.dev/service=$1-dashboard --output=jsonpath="{.items[0].metadata.name}") \
8001:8080