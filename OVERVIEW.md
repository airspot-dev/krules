# Technical Overview

## What is KRules?
KRules is an open source framework that provides, to Python developers, a flexible and fast way to build cloud native applications, creating event driven, context aware, and reactive microservices in a Kubernetes cluster.
KRules adopts a rules-based approach  based on paradigm events-condtions-actions.
KRules is inspired by [reactive manifesto](https://www.reactivemanifesto.org/en) taking full advantages of the Kubernetes cluster and Knative eventing:  
- **Responsive**: The system responds in a timely manner if at all possible;
- **Resilient**: The system stays responsive in the face of failure;
- **Elastic**: The system stays responsive under varying workload;
- **Message (Event) Driven**: The system relies on asynchronous event-dispatching to establish a boundary between components that ensure loose coupling, isolation and location transparency. 

All these features make the framework an ideal choice both for native cloud applications entirely built on top of KRules but also for integrating peripheral event driven logic into a pre-established application that becomes an event source to extend its functionalities.

The purpose of KRules is not to provide a serverless or an eventing manager infrastructure, Knative deals with that, but acts at a higher level to empower building application logic defined through rule sets in the form of Python data structures. 


## Concepts

### The subject
One of the most important concept behind the KRules  programming paradigm is **the subject**. Every time some type of event is produced, it can always be traced back to some type of entity, that produced it or that in some way is related to it.

In the KRules world this is the abstract representation around which we are shaping logic. 

KRules provides the ability to track the _state_ for the represented subjects and react to its changes. The state of subjects is defined through what we call **reactive properties**. The set of properties for a subject is dynamic and they start to exists (and consequentially the subject itself) when we assign values to them.

Behind the scenes there is a component called **Subject Property Store** that besides reactivity provides also all the facilities to work efficiently in a highly concurrent system. 

The assignment of a new value to a subject reactive property produces an event that carries both the new value and the old one. This allows the system to react not only to a new state but more widely to each state transition. 

In fact the subject could be intended as a digital twin, for example of a device which send updates about its internal temperature, a vehicle which periodically share its position, a user interacting with a web site, a document or even a kubernetes service, being kubernetes itself an event producer

In short, everything in the application domain which could produce events and could have a state is potentially a subject.

In addition to  reactive properties is possible to define also **extended properties**. 

An extended property is more like a subject’s metadata. For example, if we are dealing with devices, an extended property may be the fleet to which it belongs. Extended properties are understood by the Knative eventing infrastructure so they are more intended to define logic at the transport layer, for example, to direct all events regarding a subset of subject of the same class to a specific broker, triggering isolated group of microservices in the same cluster or even in a different one. Thinking about a real-world application, in an IoT fleet managements system they can be useful to tag each device sending a similar payload but owned by different tenants, for which we provide a set of common logics but also a more customized additional set of functionalities tailored on the specific needs and requests. Ideally, while some common logics could be activated on a public cloud, others, for performance reasons, or for relevance to sensitive data could be located on an edge infrastructure.

And now let's move on to some practical examples. 

Each ruleset resides on a Pod where is deployed the KRules base environment. We can  open a python interactive shell on a Pod _ruleset_ container to show some concepts more practically:
```sh
kubectl exec my-ruleset-pod -c ruleset -ti ipython  
```
The first step is to create a new subject:
```python
>> foo = subject_factory(“foo”)
```
If we try to access to a property of this new empty subject we get an exception:
```python
>> foo.moo
...
AttributeError: moo
```
This is because the property moo does not exist until it is assigned to the subject.
```python
>> foo.moo = 1
>> foo.moo
1
```
As previously explained, the property assignment generates an event which can subsequently be intercepted and processed by one or more rules. Looking at event display:
```
☁️  cloudevents.Event
Validation: valid
Context Attributes,
  specversion: 1.0
  type: subject-property-changed
  source: my-ruleset
  subject: foo
  id: bd198e83-9d7e-4e93-a9ae-aa21a40383c6
  time: 2020-06-16T08:16:57.340692Z
  datacontenttype: application/json
Extensions,
  knativearrivaltime: 2020-06-16T08:16:57.346535873Z
  knativehistory: default-kne-trigger-kn-channel.iot-demo-gcp-01.svc.cluster.local
  originid: bd198e83-9d7e-4e93-a9ae-aa21a40383c6
  propertyname: moo
  traceparent: 00-d571530282362927f824bae826e1fa36-a52fceb915060653-00
Data,
  {
    "property_name": "moo",
    "old_value": null,
    "value": 1
  }
```

The above is a convenient view of the event in the [CloudEvent](https://cloudevents.io/) formalization. The event consists of a set of attributes defined as an integral part of the standard and any extended attributes defined according to specific application needs. Collectively, these attributes are used for the definition of Knative triggers' filters.

(See [Knative eventing](https://knative.dev/docs/eventing/) documentation for more info)

Let’s now analyze in the most significant parts. 

First of all the event **type**. Each time a subject property is assigned or modified, an event addressed to that subject and with type **subject-property-changed** is raised. 

As you can see, the event also contains a extension called propertyname which indicates the name of the altered property. Through these attributes we are thus able to subscribe to all events relating to a variation of this property. As we will see later, it is possible to create additional attributes (as extensions) to give a more specific classification of the event, or more properly, of the related subject

Note that the name of the altered property is repeated both in the payload and as an extended property. This happens because at the transport and addressing level of the event the content of the message is not taken into account, it is instead used by the service that consumes the event (in our case a ruleset).

Looking at the content of the payload you can see how the event contains, in addition the name of the property and the new value of it, also the old property value. This is very useful when you want to implement a logic established not just on the new value of the property but also on its transitions. 

The transition between a previous and new value can often occur in a concurrent environment. Assuming that multiple processes need to update the value of the moo property, the subject's backend implementation helps to solve the problems related to concurrency and avoid conflicts and inconsistent situations supporting _atomic operations_:
```python
>> foo.moo = lambda moo: moo + 1   
```
Let's move on to an example in the real world to demonstrate how it is possible through the rules (which will be discussed later) to react to changes in a property by causing cascade effects by implementing an isolated logic.

Let’s start again creating a subject.
```
>> device = subject_factory(“device|00000A”)
```
This time, instead of a generic "foo", we have chosen a speaking name, containing some information characteristic of the subject. In this case the name  is composed of the generic category that indicates that the subject is a device with a specific unique identifier. 

We define the **tempc** property (the temperature expressed in Celsius degrees) and the thresholds in order to contextualize its value and save it in a **temp_status** property (tempc <= 20 COLD, 20 < tempc < 30 NORMAL, tempc >= 30 WARM, tempc >= 45 CRITICAL).
```python
>> device.tempc = 25
>> device.temp_status
 NORMAL
```
Assigning a value within the NORMAL range to tempc, temp_status property will not be changed.
```python
>> device.tempc = 28
>> device.temp_status
NORMAL
```
On the other hand, it can be seen that, using a value higher than the limits of the NORMAL range, the property temp_status will also be modified.
```python
>> device.tempc = 32
>> device.temp_status
WARM
```
The temp_status property transition could therefore activate further rules by triggering new  actions handled by his own isolated services (for example, turning on a fan), but also activating different operating modes. Suppose that we are monitoring the transport of perishable goods, we could activate an alert state by monitoring the time spent in an overheated status, thus generating new thresholds (the goods have been exposed too long at an inadequate temperature and will consequently be produced a notification for an operator upon reaching the next control gate).


### Rules
**Rules** are grouped into **rulesets**. The rulesets are in fact the microservices that are deployed on the cluster and respond independently to specific events type and attributes thank to Knative's triggers. There are no particular constraints on the establishment of these triggers or on what events are to be received by a ruleset. The more granular the definition of the triggers and the corresponding rulesets will be, the more resilient the resulting system will be as each service, or better said, each ruleset, is scalable independently. Inside the ruleset we can have more rules each one subscribing to different event types (if captured by the triggers) and with different activation criteria based on the received payload. Each rule, is always contextualized to a subject.

Events can be produced outside or inside the cluster 

For the outside world [Knative Eventing Sources](https://knative.dev/docs/eventing/sources/) are used. According to the Knative documentation, Event Sources are Kubernetes Custom Resources which provide a mechanism for registering interest in a class of events from a particular software system.

A growing number of already made sources are available. Anyway, Knative offers a good framework to implement new ones easily and quickly.

Going back to our example, where we are building logic around an hypothetical fleet of devices, we can have multiple sources. The most obvious one is the middleware from which we receive the devices telemetry. But before that we need to get some basic attributes of the onboarded devices like their unique identifiers, the class to which they belong to (which may imply different logics), the time within which it is expected to receive data (which can determine a state of activity or inactivity of the device), etc.

Simplifying a real case we can assume that this information will be entered into the system by loading a csv file on a storage area. The folder to which the file is uploaded will determine the class the deivice belongs to. Each row of the csv will contain the basic information of a single device.

So, what is the **source**? Who is the **subject**? What type of event is **produced**?

The source is the bucket on which the file is uploaded because the presence of a new file on the bucket can be intended as an event (the type of of the event is the _finalization_ of a write operation). The subject, however, is the file itself.

In the specific case, we assumed to use a GCP bucket where an [already made source](https://github.com/google/knative-gcp/blob/master/docs/examples/cloudstoragesource/README.md) implementation allows us to have a complete abstraction on the bucket and all the stuffs needed to get the event into our ruleset.

Once the event has been produced we intercept it in a rule, where, after downloading the file, for each line it contains, a new event addressed to each device (the new **subject**) of **type** _onboard-device_ will be emitted. Some other one or more rule, in the same or another ruleset, will be able to catch that new event activating his own logic (maybe a notification to another system or the effective registration inside the IoT middleware's device manager)

Let’s see it

The following is the data structure defining rules and it is loaded at the startup of the ruleset container. 

```python
from cloudstorage.drivers.google import GoogleStorageDriver
from krules_core.providers import subject_factory

# ...

rulesdata = [
    {
        """
        Subscribe to bucket events (finalize), import csv
        """,

        rulename: "on-csv-upload-import-devices",
        subscribe_to: "com.google.cloud.storage.object.finalize",
        ruledata: {
            filters: [
                SubjectNameMatch(  
                  "onboarding/import/(?P<deviceclass>.+)/(?P<filename>.+)", 
                  payload_dest="path_info"  # enrich payload with match
                ),
                Filter(lambda payload: payload.get("contentType") == "text/csv")
            ],
            processing: [
                ProcessCSV_AsDict(
                  driver=GoogleStorageDriver,
                  func=lambda self: lambda device_data: (
                    # a new event is issued for each line of the csv
                    self.router.route(
                        # new event type
                        event_type="onboard-device",
                        # the device becomes the new subject
                        subject=subject_factory(device_data.pop("deviceid")),
                         # device data and device class as payload
                        payload={
                            "data": device_data,
                            "class": self.payload["path_info"]["deviceclass"]
                        }),
                    )
                )
            ],
        },
    },
    # ... more rules
]
```
So the ruleset data is loaded just one time and it is static (potentially it can be even injected from the outside). However, the blocks it contains need to access runtime information that are available when an event is processed. We will come back to this later, now let's see how a rule is composed in detail.

The rule is up of 2 sections: **filters** and **processing**.

If the filter section passes the  whole processing section is executed (unless some exception is raised, we will talk about that).
Both sections are a pipeline of small functions which represent the essential building blocks of the application logic. They can be very generalized or strictly specific to application domain, and they can be considered a sort of promise hooked to the event (or events) to which the containing Rules is subscribed to. The framework encourages and promotes a high reusability of the code by providing the developer with the elements necessary to build you own blocks. We like to call them micro-assets.
At each step within the pipeline the payload can be altered enriching it with information available for subsequent blocks.


The **subscribe_to** parameter indicates the event to which the rule reacts and corresponds to the **type** attribute of the cloudevent. As described above we are only interested in _finalize_ operations. 

Following, in **ruledata** we have the pipeline composed by the **filter** and **processing** sections. 

The **filters** have 2 generic functions, already provided by the framework:

The first is [SubjectNameMatch](https://intro.krules.io/Filters.html#krules_core.base_functions.filters.SubjectNameMatch) which verifies that the subject name matches a given regular expression. Because we receive the path of the uploaded file as the subject we use it to check his location and to extract from it some useful information that we put in the payload for later use in the **processing** part. 

The next function, [Filter](https://intro.krules.io/Filters.html#krules_core.base_functions.filters.Filter), is a very general purpose function. To make it possible to use the most generic functions, an extensible mechanism to process arguments before they are passed to the function is provided. In this case we simply use a lambda function receiving the payload and a preloaded argument processor class instance recognizes its interest in the argument processing it using the required runtime information.
In this case the lambda function, thanks to the argument processors, is able to access the payload (at the stage of the pipeline processing step) and check the contentType.

After talking about generic functions, let's move on to the **processing** section where we use a more specialized function. To provide an understanding of how a function can be easily created within an application context, follow its implementation:

```python
import io
import csv
from krules_core.base_functions import RuleFunctionBase


class ProcessCSV_AsDict(RuleFunctionBase):

    def execute(self, driver, func, csvreader_kwargs={}):
        bucket = self.payload["bucket"]
        container = driver().get_container(bucket)
        blob = container.get_blob(self.subject.name)
        csv_in = io.BytesIO()
        driver().download_blob(blob, csv_in)
        csv_in.seek(0)
        with io.TextIOWrapper(csv_in, encoding="utf-8") as input_file:
            reader = csv.DictReader(input_file, **csvreader_kwargs)
            for row in reader:
                func(row)  
```
Classes derived from **RuleFunctionBase** are meta classes statically created together with the definition of the ruleset. The performing instance is created during each pipeline execution while the runtime information are injected into the object. In fact, as can be seen in the example, the payload properties are treated internally in the execute method. 

```python
# ...

rulesdata = [
    {
        rulename: "on-csv-upload-import-devices",
        subscribe_to: "com.google.cloud.storage.object.finalize",
        ruledata: {
            filters: [
                # ...
            ],
            processing: [
                ProcessCSV_AsDict(
                  driver=GoogleStorageDriver,
                  func=lambda self: lambda device_data: (
                    # Here we interact with Rule's instance "self" using a nested lambda
                    self.router.route(
                        event_type="onboard-device",
                        subject=subject_factory(device_data.pop("deviceid"), event_info=self.subject.event_info()),
                        payload={
                            "data": device_data,
                            "class": self.payload["path_info"]["deviceclass"]
                        }),
                    )
                )
            ],
        },
    },
    # ... 
]
```
Another important thing to notice is the func parameter,it should be a sort of callback to interact with each csv row and so it correctly pass as argument just the row itself. 
By the way it is possible to use a callable capable of accessing the Rule's context without it being passed inside the definition of the RuleFunction using a nested lambda, making the code simpler, more readable and generalized.

This is possible thanks to argument processors that allow you to preprocess your arguments, whether they were callable or not, to give them the context awareness.

Go to [ArgumentProcessors](https://intro.krules.io/ArgumentProcessors.html) section to learn more.

So, in the previous example, we produced an event _onboard-device_ type. Here the subject is the device and the payload contains all the initial data obtained from the csv. Somewhere in the cloud we can now intercept this event and finally setup the basic properties of each new onboarded device. To do this we define a specific Ruleset and the related Knative Trigger to intercept the *onboard-device* events.

_ruleset.py_
```python 
rulesdata = [

    """
    Set the basic properties of the device and the initial status as 'READY'
    The status will become 'ACTIVE' upon receipt of the first message
    """,
    {
        rulename: "on-onboard-device-store-properties",
        subscribe_to: "onboard-device",
        ruledata: {
            filters: [
                Filter(lambda payload: "data" in payload and "class" in payload),
            ],
            processing: [
                SetSubjectProperties(lambda payload: payload["data"]),
                SetSubjectExtendedProperty(
                    "deviceclass", 
                    lambda payload: payload["class"]
                ),
                SetSubjectProperty('status', 'READY'),
            ],
        },
    },

]
```
_triggers.yaml_
```yaml
apiVersion: eventing.knative.dev/v1
kind: Trigger
metadata:
  name: on-onboard-device-type-onboard-device
spec:
  broker: default
  filter:
    attributes:
      type: onboard-device
  subscriber:
    ref:
      apiVersion: v1
      kind: Service
      name: on-onboard-device
```
In addition, to set the basic properties, we do more few interesting things. 

We set deviceclass as an extended property. This means that from now on, this subject is tagged with that attribute and this information will be part of each event contextualized to this device. For example, we can define another Trigger for each device class to convey all these events to a dedicated broker, where a subset of rules will subscribe, activating logic specific only to that class of devices.

```yaml
apiVersion: eventing.knative.dev/v1
kind: Trigger
metadata:
  name: default-to-class-a-trigger
spec:
  broker: default
  filter:
    attributes:
      deviceclass: class-a
  subscriber:
    ref:
      apiVersion: eventing.knative.dev/v1
      kind: Broker
      name: class-a

---

apiVersion: eventing.knative.dev/v1
kind: Trigger
metadata:
  name: default-to-class-b-trigger
spec:
  broker: default
  filter:
    attributes:
      deviceclass: class-b
  subscriber:
    ref:
      apiVersion: eventing.knative.dev/v1
      kind: Broker
      name: class-b
```

We also set a status property to ‘READY’. As seen in the beginning, properties are reactive so that the system can be made aware of this new status. For example an independent service could take further steps to actually complete the onboarding procedure

This is a very important feature and, to better explain it, we can take the example presented at the beginning where, in an interactive shell, we explicitly set the received value of a temperature sensor. Now we are supposing to receive that value as part of an ingestion event. This is happening in the first rule; the following ones instead react to that change setting the temp_status property. Please note that the minimum and maximum temperatures are read as property of the subject. This is because we set them during onboarding phase by acquiring them from the csv

_ruleset.py_
```python
from krules_core.types import SUBJECT_PROPERTY_CHANGED
from krules_core.base_functions import DispatchPolicyConst

# ...

rulesdata = [

    """
    Store temp property
    """,
    {
        rulename: "on-data-received-store-temp",
        subscribe_to: "data-received",
        ruledata: {
            filters: [
                Filter(lambda payload: "tempc" in payload["data"])
            ],
            processing: [
                SetSubjectProperty("tempc", lambda payload: payload["data"]["tempc"])
            ],
        },
    },

    """
    Set temp_status COLD 
    """,
    {
        rulename: "on-tempc-changed-check-cold",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("tempc"),
                Filter(lambda self:
                       float(self.payload.get("value")) < float(self.subject.get("temp_min"))
                       ),
            ],
            processing: [
                SetSubjectProperty("temp_status", "COLD"),
            ],
        }
    },

    """
    Set temp_status NORMAL 
    """,
    {
        rulename: "on-tempc-changed-check-normal",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("tempc"),
                Filter(lambda self:
                       float(self.subject.get("temp_min")) <= float(self.payload.get("value")) < float(self.subject.get("temp_max"))
                       ),
            ],
            processing: [
                SetSubjectProperty("temp_status", "NORMAL"),
            ],
        }
    },

    """
    Set temp_status WARM 
    """,
    {
        rulename: "on-tempc-changed-check-warm",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("tempc"),
                Filter(lambda self:
                       float(self.payload.get("value")) >= float(self.subject.get("temp_max"))
                       )
            ],
            processing: [
                SetSubjectProperty("temp_status", "WARM"),
            ],
        }
    },

    """
    Since we have already intercepted the prop changed event inside the container we need to send it out 
    explicitily (both tempc and temp_status)
    """,
    {
        rulename: "temp-status-propagate",
        subscribe_to: types.SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged(
                  lambda prop: prop in ("temp_status", "tempc")
                ),
            ],
            processing: [
                Route(dispatch_policy=DispatchPolicyConst.DIRECT)
            ]
        },
    },
]
```
_triggers.yaml_
```yaml
apiVersion: eventing.knative.dev/v1
kind: Trigger
metadata:
  name: on-data-received-set-temp-status-type-data-received
spec:
  broker: class-a
  filter:
    attributes:
      type: data-received
  subscriber:
    ref:
      apiVersion: v1
      kind: Service
      name: on-data-received-set-temp-status
---
apiVersion: eventing.knative.dev/v1
kind: Trigger
metadata:
  name: on-propchange-tempc
spec:
  broker: class-a
  filter:
    attributes:
      type: subject-property-changed
      propertyname: tempc
  subscriber:
    ref:
      apiVersion: v1
      kind: Service
      name: on-data-received-set-temp-status
```

The last rule needs some more explanation. Because when an event is emitted it is first managed inside the container and then propagated outside only if no subscriber is found, we need to create a rule to explicitly dispatch the **subject-property-changed** event outside, if we want to give the opportunity to other services to react to this change. 

As can be seen, some RuleFunctions use lambda functions as parameters that have the payload or subject as arguments, this is possible thanks to argument processors.

Go to [ArgumentProcessors](https://intro.krules.io/ArgumentProcessors.html) section to learn more.

Since we want to apply this logic only to a specific device class, we can take advantage of the event sorting mechanism through the extended properties illustrated above by associating both triggers with the **class-a** broker.


Another interesting thing to note is that the **subject-property-changed** event contains the propertyname as an extended property.

## Observability and errors management
Everything is an event, also the very fact that a rule is processed is itself an event. This is because the rules, during their processing, produce a detail metric, in the form of an event, relative to each process step of the pipeline in which they are contained.
```
{'event_info': {'Id': '393b237d-2529-46d4-865f-42bd6612bd73',
                 'Knativearrivaltime': '2020-06-15T09:44:52.668735338Z',
                 'Knativehistory': 'default-kne-trigger-kn-channel.iot-demo-gcp-01.svc.cluster.local',
                 'Originid': '393b237d-2529-46d4-865f-42bd6612bd73',
                 'Source': 'metrics-got-errors',
                 'Specversion': '1.0',
                 'Subject': 'onboarding/import/class-b/nonsense.csv',
                 'Time': '2020-06-15T09:44:52.657766Z',
                 'Traceparent': '00-e2f244152a7c8d89a163e6974e626d07-d001a8c1bf4fe22c-00',
                 'Type': 'on-gcs-csv-upload-errors'},
 'filters': [{'args': ['onboarding/import/(?P<deviceclass>.+)/(?P<filename>.+)'],
              'func_name': 'CheckSubjectMatch',
               'kwargs': {'payload_dest': 'path_info'},
               'payload_diffs': [],
               'returns': True},
              {'args': ['True'],
               'func_name': 'Filter',
               'kwargs': {},
               'payload_diffs': [],
              'returns': True}],
 'got_errors': True,
 'message': 'com.google.cloud.storage.object.finalize',
 'payload': {'bucket': 'krules-dev-demo-02',
             'contentType': 'text/csv',
             'id': 'krules-dev-demo-02/onboarding/import/class-b/nonsense.csv/1592214290865122',
             'kind': 'storage#object',
             'name': 'onboarding/import/class-b/nonsense.csv',
             'size': '60',
             'storageClass': 'STANDARD',
             'timeCreated': '2020-06-15T09:44:50.864Z',
             'timeStorageClassUpdated': '2020-06-15T09:44:50.864Z',
             'updated': '2020-06-15T09:44:50.864Z'},
 'processed': True,
 'processing': [{'args': [],
                 'exc_extra_info': {'args': ['deviceid']},
                 'exc_info': ['Traceback (most recent call last):\n',
                              '  File '"/usr/local/lib/python3.7/site-packages/krules_core/core.py", '
                              'line 149, in '_process\n'
                              'event_info=self.subject.event_info()),\n',
                              ...
                              'KeyError:"deviceid"\n'],
                 'exception': 'builtins.KeyError',
                 'func_name': 'ProcessCSV_AsDict',
                 'kwargs': {'bucket': 'krules-dev-demo-02',
                 'driver': <class 'abc.ABCMeta'>,
                 'func': '<lambda>'},
                 'payload_diffs': [],
                 'returns': None}],
 'rulename': 'on-csv-upload-import-devices-error',
 'subject': 'onboarding/import/class-b/nonsense.csv'}
```

As we can see in this trace event, referring to the rule of the csv loading in the previous example, the payload was altered during the blocks execution (acquiring information such as the file name and the device class). We focus on the **got_errors** entry, which indicates whether or not an exception was raised during the execution of the rule. In this case it is _True_ and that means that some problems was encountered during the rule execution (maybe for a badly formatted or even damaged file). Furthermore, while the metrics of the rules that have been executed correctly have remained unchanged, all the information useful for managing them has been added to the metrics of the rule that generated the exception: the exception type, the exception args and the stack trace. Now we can implemented a logic to handle rulesets exceptions in a general way. 

```python
from krules_env import RULE_PROC_EVENT

# ...

rulesdata = [

    """
    Give the chance to subscribe specific error conditions from the source originating the error
    """,
    {
        rulename: "on-errors-propagate",
        subscribe_to: RULE_PROC_EVENT,
        ruledata: {
            filters: [
                Filter(lambda payload: payload["got_errors"])
            ],
            processing: [
                Route(
                    event_type=lambda payload: 
                      "{}-errors".format(payload["_event_info"]["Source"]),
                    subject=lambda payload: payload["subject"],
                    payload=lambda payload: payload
                )
            ],
        },
    },
]
```

In this case we decide to propagate the error message to the ruleset that generated it and delegate to original ruleset the exception handling.
```python
from cloudstorage.drivers.google import GoogleStorageDriver
# other import

# ...

rulesdata = [

    """
    Subscribe to storage, import csv
    """,
    {
      # ...
    },

    """
    Manage generic import errors (reject file)
    """,
    {
        rulename: 'on-csv-upload-import-devices-error',
        subscribe_to: "on-gcs-csv-upload-errors",
        ruledata: {
            filters: [
                Filter(lambda payload: payload["rulename"] == "on-csv-upload-import-devices")
            ],
            processing: [
                # reject file
                DeleteBlob(
                    driver=GoogleStorageDriver,
                    bucket=lambda payload: payload["payload"]["bucket"],
                    path=lambda payload: payload["payload"]["name"]
                )
            ]

        }
    },

]
```
We have added a rule that received an error event, or better, the error event propagated by the rule we have just defined, and the name of the file that raised the exception (in the payload) will remove the above mentioned file.

This mechanism handles exceptions in a very general and basic way, we can have multiple generic strategies to handle exceptions. For example, we can integrate with specialized platforms and collect the stacktrace to send it on common notification systems. We can also store all events containing errors on a database with all data related to the original event in order to reproduce it again after fixed the problem. 

There are also many cases where an error is predictable and we want define some recovery logic in the real time. 

KRules provides and allows to write new _exception dumpers_ to give more detailed extra information about a specific exception (for example a timeout or a bad http status code). This information is obviously available for creating rules

Suppose we want to post the data processed by rules on an external API server and we want to manage the case in which the service becomes unavailable for maintenance (status code 503).

```python
rulesdata = [

    """
    Do call api
    """,
    {
        rulename: "on-do-extapi-post",
        subscribe_to: "do-extapi-post",
        ruledata: {
            processing: [
                PostExtApi(
                    url=lambda payload: payload["url"],
                    data=lambda payload: payload["req_data"],
                    on_response=lambda resp: (
                        resp.raise_for_status(),
                        resp.status_code == 503 and resp.raise_for_status()
                    )
                )
            ]
        }
    },

    """
    Manage exception, retry in 10 seconds
    """,
    {
        rulename: "on-do-extapi-post-errors",
        subscribe_to: "{}-errors".format(os.environ["K_SERVICE"]),
        ruledata: {
            filters: [
                Filter(lambda payload:
                       payload.get("rulename") == "on-do-extapi-post" and
                       jp.match1("$.processing[*].exception", payload) == "requests.exceptions.HTTPError" and
                       jp.match1("$.processing[*].exc_extra_info.response_code", payload) == 503)
            ],
            processing: [
                Schedule(
                    event_type="do-extapi-post",
                    payload=lambda payload: payload["payload"],
                    when=lambda _: (datetime.now() + timedelta(seconds=10)).isoformat(), replace=True),
            ]
        }
    }

]
```
The first rule make the call to the service and raise an exception in case it is not successful, the second one intercepts any error and, if the exception is linked to the 503 state, we suppose the problem is temporary so the event triggering the first rule is scheduled in 10 seconds. This mechanism allows, even in cases of absence of service, to not lose any data and, once it is available again, to resume any application flow linked to the response of the API. Obviously this is an extreme simplification but it can make the idea about how much control and flexibility we can have.  This can be very useful in a distributed asynchronous system where a single service failing can lead to an incomplete and inconsistent situation.