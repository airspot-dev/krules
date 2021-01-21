# IoT demo application

The aim of this demo is to highlight some KRules core concept like the **subject** and its **reactive properties**. 
Reactive properties are used to map a data stream context (e.g. a digital twin of a device or a twin of a 
Kubernetes resource) and to give them a state to which changes business logic can react. This behavior 
is shown through this demo in an IoT scenario. In the demo the business logic reacts seamlessly to devices’ 
produced metrics (e.g. temperature) and to Kubernetes resources update events. When it comes to Kubernetes 
resources we gather pieces of information useful for application logic and we set them as reactive 
properties. This case is exemplified in the demo through the scenario in which is created a new Knative 
service for which we want to listen and react when a URL becomes available or changes following the 
provisioning of the SSL cert. All this logic is developed very easily using KRules reactive properties.

The Demo also wants to focus on how easy it is to take full advantage of Knative eventing, using brokers 
and triggers and shape logic upon them using subjects extended properties. Any time a _CloudEvent_ related 
to a specific device (the subject) is produced, its metadata automatically contains those properties 
determining the activation or not of specific groups of rulesets (business logic).

Demo starts from uploading a .csv file, containing the base information about a set of devices, on a 
Google Cloud Storage bucket. This bucket is bound by a Knative CloudStorageSource, and a ruleset subscribes 
to the produced CloudEvents. A device’s subject is created for each line of the csv file. Depending on which 
folder the file was uploaded, an **extended property** is set defining an hypothetical "device class". 
The device class conditions all subsequent events related to the device allowing triggers to act differently. 
In the demo telemetry data are routed on a common broker but they are also split in two different brokers, 
each specific for each device class. This architecture allows the activation of a common business logic 
for all devices (eg: monitoring the _receiving data_ state) and the activation of a specific business logic 
for each device class. This result is achieved quite simply by subscribing to the appropriate broker. 
In the demo we have specific business logic related to temperature for the first device class and specific 
business logic related to geo positioning for the second device class.

For the data ingestion we will simply use an http endpoint provided by a serverless Knative service. 
The Knative service (and its related secret containing the api key) is created from a database model. 
The database model is generated in a simple Django application. An ad-hoc extension was developed. 
This extension produces cloudevents for any create/update/delete operation on Django ORM for the models 
we are interested in. Each update operation originates a new Knative service revision. 
This behavior makes the Django application acting as another Knative source.

Another aspect the demo focuses on is the **observability** of rules activity. 
This characteristic can help developers in writing applications but it can also be used as part of the 
application itself. When an event is processed by a rule another event is generated: the event 
“rule X has processed event Y”. This new event gathers all execution runtime information, including errors. 
These events are all routed on their own broker which of course can be subscribed in order to build new logic. 
All of this can be particularly useful for general or specific **error management**. 
In fact the services producing errors and the ones specialized to manage errors will be totally decoupled, 
agnostic and independent. Such a characteristic can be a great advantage in a distributed and asynchronous 
application, the typical nature of a microservices architecture that takes full advantage of event driven 
paradigm.

For more detailed information about how the demo works you can take a look to [these slides](https://github.com/airspot-dev/iot-demo/blob/master/Diagrams.pdf)

Note that neither a step-by-step installation guide nor an illustrating video for this demo exist yet, but, 
if you are interested in knowing more about the project or even contribute to it, don't hesitate 
to [contact us](mailto:info@airspot.tech)
