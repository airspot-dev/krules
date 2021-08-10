# KRules : Getting started

## Setting up the environment

To run KRules, you need to have a working [Python](https://python.org) environment. We support versions from `Python 3.8.x`.

You will also need `pip` to install all the required packages.

### Creating the Knative cluster

> **Are you a KNative developer? Probably your environment is already set up and you can skip this section**

First of all you need a working Kubernetes Cluster, please refer to the [kubernetes documentation](https://kubernetes.io/docs/tutorials/kubernetes-basics) about the creation of a cluster in your personal cloud, or just use a managed cluster from a cloud provider (AWS, GCP, Azure, etc...).

After that, you need to install Knative in your cluster, to
do that you need to follow the steps in the
[official Knative documentation](https://knative.dev/docs/admin/install).

> Note that for the framework to work properly, you just
> need to install the **Knative Eventing**, while the other
> Knative features are not mandatory.

Once you completed all those steps, you are ready to create
and maintain KRules projects, using the KRules CLI.

## The KRules CLI

To create a new project we leverage the power of the
[***KRules CLI (TODO, PUT LINK)***](./TODO).

### Installing the CLI

Just run the following command to install the CLI in your
system:

``` bash
pip install krules-cli
```

After installing the CLI you can use it to manage your KRules projects

### Setting up a new project

To set up a new project run:

``` bash
krules scaffold create project-name /path/of/project/root
```

The CLI will automatically create the project scaffolding for you. You can also tweak the CLI behaviour by using some enviroment variables, check the reference [**HERE (TODO POINT TO THE KRULES CLI DOC CONTAINING ENV REFERENCE**](./TODO)