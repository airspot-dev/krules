import pykube
from pykube.objects import NamespacedAPIObject


def get_api():

    config = pykube.KubeConfig.from_env()
    return pykube.HTTPClient(config)


class Broker(NamespacedAPIObject):

    version = "eventing.knative.dev/v1"
    kind = "Broker"
    endpoint = "brokers"


def get_cluster_brokers(flat=False):

    api = get_api()
    available_brokers = []
    for broker in Broker.objects(api).all():
        if flat:
            available_brokers.append(broker.name)
        else:
            available_brokers.append((broker.name, broker.name))
    return available_brokers


class Trigger(NamespacedAPIObject):

    version = "eventing.knative.dev/v1"
    kind = "Trigger"
    endpoint = "triggers"


class ContainerSource(NamespacedAPIObject):

    version = "sources.knative.dev/v1"
    kind = "ContainerSource"
    endpoint = "containersources"
