# KRules project template

This repo provides the base structure to easily start to create your own project using the [KRules framework](https://github.com/airspot-dev/krules).

This is not just a step by step guide showing you how to create a new project starting from the provided base structure 
and how to customize and adapt it to your own environment. It also wants to introduce you to some basic KRules concepts. 

More documentation will follow, for now, you can also read our [overview](https://intro.krules.io/OVERVIEW.html)
if you are interested to go more deeply into the concepts of the KRules framework.

## Requirements

- An up and running **Kubernetes cluster**. To take your first steps you can use a more developer-friendly local 
installation like, for example, minikube, Kind or whatever you prefer;
- A **Knative** updated version working installation (including serving and eventing). You can 
follow [the official Knative installation guide](https://knative.dev/v0.19-docs/install/any-kubernetes-cluster/) 
or opt for a simpler installation using [Mink](https://github.com/mattmoor/mink);
- In order to configure a subjects storage provider, you need at least a **Redis** or a **MongoDB** database;
- A working **Docker** installation and a registry accessible from the cluster to push your images to. 
This is needed in order build and publish your rulesets.

## Choosing the right subjects storage provider backend 

[_Subjects_](https://intro.krules.io/en/0.8/OVERVIEW.html#concepts) are a core concept of KRules framework.
We need a storage database solution to store subjects and their properties, currently, Redis and MongoDB 
are supported.

- **Redis** :

    Redis is fast and naturally suitable to be safe in a high concurrency environment, for example where 
    subjects own properties acting like counters accessed and modified simultaneously from multiple services. 

    Unless you have specific scalability needs, in terms of the unpredictable amount of subjects to create, 
    Redis is the recommended choice.

- **MongoDB**:

    If you cannot predict how many subjects will be created during your app execution and you don't want to 
worry about dismissing unnecessary ones (subjects who are no longer involved in the business logic and 
won't receive or produce events anymore) you may need a more scalable solution. 

Note,you can use both solutions at once. You can configure your environment to use 
one backend or another depending on the kind of subject you're referring to. More explainations will follow later. 

## Install KRules base system

Once all previously mentioned requirements are satisfied you can proceed with the installation of KRules base 
system running:

```
$ kubectl apply -f https://github.com/airspot-dev/krules-controllers/releases/download/v0.8.1/release.yaml
```

:warning: **WARNING**: Ensure that all pods are in a `Running` status and all container are `READY` before run the previous command. If you have installed
Knative in a standard way you can check pods status in **knative-eventing** and **knative-serving** namespaces. While if you had chose to use Mink 
check **mink-system** namespace.

This command will install various kinds of stuff in the `krules-system`  namespace.
Most of them are Knative services able to scale to zero, so if you want to check the installation status run the 
following command:

```
$ kubectl -n krules-system get ksvc
```

Wait until all the service show a status `READY` equal to `True`.

## Preparing your project namespace

In order to work with KRules having a dedicated namespace for each project is the recommended practice.

So let's start from create a new namespace: 

```
$ kubectl create ns my-project
```

KRules requires that some basic stuff are present in your namespace.

We don't want to go too deep for now because KRules injects in your namespace all that it needs.

To accomplish that you can just label your namespace as follow: 

```
$ kubectl label ns my-project krules.airspot.dev/injection=enabled
```

If everything went well, looking at the pods in your namespace, you should see something like this:

```
$ kubectl get po -n my-project
NAME                                                      READY   STATUS  RESTARTS  AGE
apiserversource-krules-injected1778c84e8e0fc5b29e01       1/1     Running 0         48s
```

## Download the project template

Now it's time to download the base structure of your project.

### If you have a Github account

If you have a GitHub account you can start by using this repo as a template to fork directly to your own project. 

You can just click on "Use this template" as shown below.

![UseThisTemplate](https://github.com/airspot-dev/krules/blob/main/.support/UseThisTemplate.png)

Follow the Github instructions to create your own repository then clone it and start work.

### If you don't have a Github account

First, create an empty repository wherever you want.

Then clone the template repository:
```
$ git clone https://github.com/airspot-dev/krules-project-template.git my_project
```

Finally replace origin with own repository url and push to your new repository:
```
$ cd my_project
$ git remote set-url origin <your repository>
$ git push -u
```

### Configure your environment

According to your previous subjects storage choice, you have to modify the related **ConfigurationProviders**.

A ConfigurationProvider is a CustomResource that provides the ability to inject a given configuration to Knative 
services (our rulesets) depending from their labels.

You can find them in the `${PROJECT_DIR}/base/k8s`:

```
.
├── base
│   ├── ...
│   └── k8s
│       ├── config-krules-subjects-mongodb.yaml
│       ├── config-krules-subjects-redis.yaml
│       └── kustomization.yaml
├── ...
```

A ConfigurationProvider contains the following elements in the spec section:

- **key**: You don't have to change this attribute for these two providers. This will be used by the rulesets to access 
the content of the data section;

- **applyTo**: It is the selector to match services to apply the configuration to, as same as key section you can leave 
this section unchanged;

- **data**: It is a dictionary containing all the configuration information we want to provide. It supports the 
environment variable substitution;

- **container**: If no name is provided it refers to ruleset container. This section is useful to provide all 
environment variables referred to in the data section. Commonly this is made using a secret but it is not mandatory.

Note that in both provided configurations we refer to a secret that you need to create on your 
own following our indication or in the way is more suitable for you.

On how to create secrets refer to 
[Define container environment variables using Secret data](https://kubernetes.io/docs/tasks/inject-data-application/distribute-credentials-secure/#define-container-environment-variables-using-secret-data).

Once you well configured your ConfigurationProvider you have to uncomment it in `kustomization.yaml`.

```
resources:
# - config-krules-subjects-redis.yaml
# - config-krules-subjects-mongodb.yaml
```

:warning: **WARNING**: Wait to apply the configuration. It will be done later.

## Build the base image

All rulesets are in fact Knative services running a docker container based on the images you build and then deploy on 
your cluster. All services share a common configuration in order to be made aware of how to connect to your subjects 
storage instance and more.

In the same way, each rules needs to access a base environment configuration, which is contained in the base image of 
the KRules.

In order to a rules to be able to access both the basic configuration and the project specific ones, there must be an 
intermediate layer.

In this section we will explain how to create a base image that has all the environment available and which will then be 
extended by all your rulesets.

### Enable subjects storage on your code

First, you need to tell your application how to handle your previously chosen storage solution.

We extensively use the principle of _Inversion of control_ (IoC) injecting in some providers a specific component 
implementation. For example, any time a subject is referred, its registered storage provider's factory is invoked. The 
factory is a _callable_ receiving the following parameters:

- **name**: Is the name that uniquely identifies the subject;

- **event_info**: A dictionary containing details about the received CloudEvent metadata;

- **event_data**: The received payload.

Usually, we only need the _name_ parameter which acts as a discriminant to determine which kind of subject it is and 
consequently which component to instantiate for (ex: Redis or MongoDB implementation). We provide a skeleton 
that you can easily use without the need to understand it too deeply, although the mechanism is open and you can customize it 
for your special needs.

To define your environment's storage configuration go to `${PROJECT_DIR}/base/app/env.py`.

```
.
├── base
│   ├── ...
│   └── app
│       ├── app_functions/
│       └── env.py
├── ...
```

Uncomment the portion of code corresponding to the type of storage you have decided to use.

Note also how configurations are managed. We have a configuration provider gathering the parameter values we need in 
the form of a dictionary. Come back and look at the _ConfigurationProvider_ resources you previously edited and 
particularly to their _key_ and _data_ attributes, notice how the configuration was injected and acquired by the provider.


The proposed code blocks are fine if you want to use only one type of storage. 

You have great flexibility on how to manage multiple backends for the different needs you may have in your own project.


Take a look at this example:

```python
from dependency_injector import providers as providers
from krules_core.providers import (
    subject_storage_factory,
    configs_factory
)


def init():

  from k8s_subjects_storage import storage_impl as k8s_storage_impl
  from redis_subjects_storage import storage_impl as redis_storage_impl
  from mongodb_subjects_storage import storage_impl as mongo_storage_impl
  
  # mongoDB
  subjects_mongodb_storage_settings = configs_factory() \
      .get("subjects-backends") \
      .get("mongodb")
  
  client_args = subjects_mongodb_storage_settings["client_args"]
  client_kwargs = subjects_mongodb_storage_settings["client_kwargs"]
  database = subjects_mongodb_storage_settings["database"]
  collection = subjects_mongodb_storage_settings.get("collection", "subjects")
  
  #redis  
  subjects_redis_storage_settings = configs_factory() \
      .get("subjects-backends") \
      .get("redis")
  
  subject_storage_factory.override(
      providers.Factory(lambda name, **kwargs:
                          name.startswith("epc:") 
                          and mongo_storage_impl.SubjectsMongoStorage(
                              name,
                              database,
                              collection,
                              client_args=client_args,
                              client_kwargs=client_kwargs,
                          )
                          or redis_storage_impl.SubjectsRedisStorage(
                              name,
                              subjects_redis_storage_settings.get("url"),
                             key_prefix=subjects_redis_storage_settings.get("key_prefix")
                          )
                        )
  )
```

We assumed here that we are tracking items for a supply chain application where each of them, according to a GS1 
specification, is identified by its [EPC code](https://www.epc-rfid.info/) which universally identify the corresponding 
physical object. Potentially, they could be billions. We are also tracking different entities (eg. warehouses, 
manufacturer, scanner, etc ...), some of them directly related to EPCs, accessed very often and concurrently, for 
example, any time a related item produces or receive some kind of event. However they are In a fewer and more predictable 
number, so we'd like to keep them all backed by Redis.


> :eyes: &nbsp; An important point that needs to be discussed here is that the chosen database solution for the subjects storage 
implementation doesn't correspond to the database you may choose to give safe persistence to all data regarding the 
entities related to your application even if they actually have an exact match with subjects. They are two totally 
different things. Subjects are meant to be the reactive part of your application and consequentially the contexts of the 
rules we'll define. They are always accessed directly by name and we can't do queries like _"give me all subjects having this value for that property"_. 
You still need to have a more usual database solution for that, which one is totally up to you and, easily, in the 
context of a KRules based application, its records will be kept updated by some rule reacting to some subject's state 
changes.


### Build and deploy the image

Now that the providers are properly configured, it's time to build your base image.

First, you need to configure the following environment variables:

- **PROJECT_DIR**: the absolute path of your project root;

- **DOCKER_REGISTRY**: the docker registry where your rulesets images will be pushed to;

- **NAMESPACE**: the Kubernetes namespace where you want to deploy your project resources, the one you have created in 
the previous steps;

- **KRULES_APPLICATION**: your application name, this params will be basically used to compose your base image name.

```
$ export PROJECT_DIR=$HOME/Dev/my_project/
$ export DOCKER_REGISTRY=docker.io/my-dockerid
$ export NAMESPACE=my-project
$ export KRULES_APPLICATION=my-project
```

Once your local environment is well configured run **deploy.sh** script.

```
$ $PROJECT_DIR/base/deploy.sh
```

This script, in addition to deploying the chosen configuration providers, will build the base image, push it to your 
Docker registry and create a ConfigMap called **config-krules-project** to keep track of the latest deployed version 
used by the rulesets build process.

## Create your own rulesets

Now that the base project structure is ready move on how to create rulesets.

In your newly created project, there is a **scripts** folder that provides some facilities to easily create and deploy 
your rulesets.

```
.
├── base/
├── rulesets/
└── scripts
    ├── __init__.py
    ├── requirements.txt
    └── ruleset.py
```

Before you can use them you need to install the necessary packages, to do this run:

```
$ pip install -r ${PROJECT_DIR}/scripts/requirements.txt
```

Now you can finally create your first ruleset, to do this run:

```
$ $PROJECT_DIR/scripts/ruleset.py create my-awesome-ruleset -p ${PROJECT_DIR}/rulesets
```

This will create a new folder called my-awesome-ruleset in your rulesets folder.

The **-p** argument is optional and indicates which is the parent folder of the new ruleset, if omitted it will be in 
the current folder.


We prefer to put all rulesets in a dedicated folder, intuitively called rulesets, but it's not mandatory, feel free to 
use any folder structure you like as this choice only serves to organize your work and has no real effect on the 
deployment and functionality.


Let's come back to the new ruleset folder.

```
rulesets
└── my-awesome-ruleset
    ├── README.md
    ├── __deploy__.py
    ├── ruleset.py
    └── ruleset_functions
        └── __init__.py
```

It contains:

- **README.md**: an .md file where you can (and should) put a brief description of your ruleset; 

- **__deploy__.py**: a python file where you will put all the information related to the deployment of the ruleset, for 
example, the definition of the triggers, the service labels, etc;

- **ruleset.py**: a python file where you will define your ruleset;

- **ruleset_functions**: a folder where you will define your custom rules and the ruleset specific functions. Again, 
it is not mandatory but just a hint of how to organize your code. By default, each python module (a folder containing 
an __init__.py) in the ruleset folder is automatically added to the resulting container.


Except for the README, the content and functionality of these elements will be explained in depth in the next sections.

### __deploy__.py

As said before this file contains all the information useful to the script to build and push the ruleset image and to 
deploy all the resources needed, basically the ruleset knative service and triggers having it as a subscriber.

```python
name = "my-awesome-ruleset"

add_files = (
    "ruleset.py",
)

add_modules = True  # find modules in directory (folders having __init__.py file) and add them to container

extra_commands = (
#    ("RUN", "pip install my-wonderful-lib==1.0"),
)

labels = {
    "serving.knative.dev/visibility": "cluster-local",
    "krules.airspot.dev/type": "ruleset",
    "krules.airspot.dev/ruleset": name
}

template_annotations = {
    #"autoscaling.knative.dev/minScale": "0",
}

#service_account = "my-service-account"

triggers = (
   {
       "name": "my-awesome-trigger",
       "filter": {
           "attributes": {
               "type": "my-type"
           }
       }
   },
)
triggers_default_broker = "default"

ksvc_sink = "broker:default"
ksvc_procevents_sink = "broker:procevents"
```

Most of the content of the file is easily understandable. For a better understanding read the 
[Knative eventing](https://knative.dev/v0.19-docs/eventing/) documentation

### ruleset.py

This file contains your ruleset logic.

```python
from krules_core.base_functions import *
from krules_core import RuleConst as Const

from krules_core.providers import proc_events_rx_factory
from krules_env import (
  publish_proc_events_errors, 
  publish_proc_events_all,
  # publish_proc_events_filtered
) 

try:
    from ruleset_functions import *
except ImportError:
    # for local development
    from .ruleset_functions import *


rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING


# proc_events_rx_factory().subscribe(
#   on_next=publish_proc_events_all,
# )
proc_events_rx_factory().subscribe(
 on_next=publish_proc_events_errors,
)

rulesdata = [
    """
    Rule description here..
    """,
    {
        rulename: "rule-name",
        subscribe_to: ["event-type"],
        ruledata: {
            filters: [],
            processing: []
        }
    },
    # more rules here..
]
```

All rules, which compose the ruleset logic, are declared within **rulesdata**.

We won't explain what each rule does, because that's outside the scope of this document, but if you want to learn more, 
you can consult our [base functions overview](https://intro.krules.io/BaseFunctions.html).

An important thing to notice is the observability definition.

It is possible to decide what to do with the 
[resulting ruleset processing events](https://intro.krules.io/OVERVIEW.html#observability-and-errors-management)
just notice how we use another provider onwing an RX ReplySubject instance, deciding, by default, only to publish events 
when some exception is raised processing the rules.

## What to do now

This guide, of course, is not enough to get you started building your first micro-services event-driven 
application using KRules. Please be confident and patient while we're working hard to provide you new useful 
documentation to help you being profitable using KRules and of course, its stack which is based upon like KNative 
eventing and python.


In the meantime, if you have the soul of a pioneer, take a look at some code in our repositories. For example:

- [iot demo](https://github.com/airspot-dev/iot-demo)

- [blue-green demo](https://github.com/airspot-dev/knative-bluegreen-demo)

:heart: &nbsp; Of course, we are, love and support pioneers, so don't esitate to [contact us](mailto:info@airspot.tech):email:

