import os

import pytest

import pykube

from krules_core.providers import subject_storage_factory, subject_factory
from krules_core.tests.subject.sqlite_storage import SQLLiteSubjectStorage
from k8s_subjects_storage import storage_impl as k8s_storage_impl
from dependency_injector import providers
import random, string

POD_NAME = ""
NAMESPACE = ""

def setup_module(_):

    extra_kwargs = {}
    if os.environ.get("API_URL", False):
        extra_kwargs.update({
            "override_api_url": os.environ.get("API_URL")
        })

    def _raise():
        raise Exception("No subject storage provider overridden")

    subject_storage_factory.override(
       providers.Factory(lambda name, event_info, event_data:
                         name.startswith("k8s:") and k8s_storage_impl.SubjectsK8sStorage(
                                                                                    resource_path=name[4:],
                                                                                    resource_body=event_data
                         )
                         or _raise())
    )

    global POD_NAME, NAMESPACE

    POD_NAME = "pytest-temp-{0}".format(
        ''.join(random.choice(string.ascii_lowercase) for i in range(8))
    )

    if os.environ.get("API_URL", False):
        config = pykube.KubeConfig.from_url(os.environ.get("API_URL"))
    else:
        config = pykube.KubeConfig.from_env()

    if os.environ.get("NAMESPACE", False):
        NAMESPACE = os.environ.get("NAMESPACE")
    else:
        NAMESPACE = config.namespace

    # create a test pod
    obj = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": POD_NAME,
            "namespace": NAMESPACE,
            "labels": {
                "app": "pytest-temp"
            }
        },
        "spec": {
            "containers": [{
                "name": "hello",
                "image": "karthequian/helloworld"
            }]
        }
    }
    api = pykube.HTTPClient(config)
    pykube.Pod(api, obj).create()


def teardown_module(_):
    subject_storage_factory.reset_last_overriding()

    global POD_NAME, NAMESPACE

    if os.environ.get("API_URL", False):
        config = pykube.KubeConfig.from_url(os.environ.get("API_URL"))
    else:
        config = pykube.KubeConfig.from_env()
    api = pykube.HTTPClient(config)
    pykube.Pod.objects(api).filter(namespace=NAMESPACE).get(name=POD_NAME).delete()


def test_inferred_properties():
    global POD_NAME, NAMESPACE

    pod = subject_factory(f"k8s:/api/v1/namespaces/{NAMESPACE}/pods/{POD_NAME}/status", event_data={})

    assert pod.ext_name == pod.get_ext("name") == POD_NAME
    assert pod.ext_namespace == pod.get_ext("namespace") == NAMESPACE
    assert pod.ext_group == pod.get_ext("group") == "core"
    assert pod.ext_apiversion == pod.get_ext("apiversion") == "v1"
    assert pod.ext_resourcetype == pod.get_ext("resourcetype") == "pods"
    assert pod.ext_subresource == pod.get_ext("subresource") == "status"


def test_props():
    pod = subject_factory(f"k8s:/api/v1/namespaces/{NAMESPACE}/pods/{POD_NAME}", use_cache_default=True)

    assert pod.ext_name == pod.get_ext("name") == POD_NAME

    with pytest.raises(AttributeError):
        pod.get("p1")

    pod.p1 = 1
    pod.ext_p2 = "p2"

    pod.store()

    pod = subject_factory(f"k8s:/api/v1/namespaces/{NAMESPACE}/pods/{POD_NAME}", use_cache_default=True)

    assert pod.p1 == 1
    pod.p1 = lambda p: p+1
    assert pod.p1 == 2

    pod_nc = subject_factory(f"k8s:/api/v1/namespaces/{NAMESPACE}/pods/{POD_NAME}", use_cache_default=False)
    assert pod_nc.p1 == 1
    pod.store()
    assert pod_nc.p1 == 2
    del pod.p1
    pod.store()
    with pytest.raises(AttributeError):
        pod_nc.get("p1")



