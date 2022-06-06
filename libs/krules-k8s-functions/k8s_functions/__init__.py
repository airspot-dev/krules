from .functions import *

from pykube.objects import NamespacedAPIObject


class ConfigurationProvider(NamespacedAPIObject):

    version = "krules.dev/v1alpha1"
    kind = "ConfigurationProvider"
    endpoint = "configurationproviders"