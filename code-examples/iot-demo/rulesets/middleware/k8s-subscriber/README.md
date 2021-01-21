# k8s-subscriber

Here we subscribe directly the API Server Source 
which captures events regarding knative services labeled as *endpoint* or *dashboard*

When the service becomes available his URL is set 
as a reactive property on a specific subject representing the service twin
allowing other rulesets to react