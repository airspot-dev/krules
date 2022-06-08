import pykube
from pykube.objects import NamespacedAPIObject


def get_api():

    config = pykube.KubeConfig.from_env()
    return pykube.HTTPClient(config)


class Broker(NamespacedAPIObject):

    version = "eventing.knative.dev/v1"
    kind = "Broker"
    endpoint = "brokers"


class KService(NamespacedAPIObject):

    version = "serving.knative.dev/v1"
    kind = "Service"
    endpoint = "services"


class Trigger(NamespacedAPIObject):

    version = "eventing.knative.dev/v1"
    kind = "Trigger"
    endpoint = "triggers"


class ContainerSource(NamespacedAPIObject):

    version = "sources.knative.dev/v1"
    kind = "ContainerSource"
    endpoint = "containersources"


class ConfigurationProvider(NamespacedAPIObject):

    version = "krules.dev/v1alpha1"
    kind = "ConfigurationProvider"
    endpoint = "configurationproviders"