# django-orm-to-k8s

Responds to the events of creation / modification / deletion of the Fleet (middleware) model on the django orm,
creating, modifying or destroying the revisions of the related knative services on kubernetes

the connected services are an endpoint for the ingestion of data by the devices with its api_key secret
and a dashboard in charge of receiving notifications on a websocket channel
regarding the activity of the devices belonging to the fleet managed by the middleware
