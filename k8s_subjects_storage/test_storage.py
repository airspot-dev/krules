# Copyright 2019 The KRules Authors
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import pykube
import pytest
from dependency_injector import providers
from k8s_subjects_storage import storage_impl
from krules_core.providers import subject_storage_factory

from krules_core.subject import SubjectProperty, SubjectExtProperty, PropertyType

POD_NAME = ""
NAMESPACE = ""


def setup_module(_):
    import random, string

    extra_kwargs = {}
    if os.environ.get("API_URL", False):
        extra_kwargs.update({
            "override_api_url": os.environ.get("API_URL")
        })

    subject_storage_factory.override(
        providers.Factory(
            lambda resource_path, resource_body=None:
                storage_impl.SubjectsK8sStorage(resource_path, resource_body, **extra_kwargs)
        )
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

def test_factory_base_properties():

    endpoints = [
        ("/apis/apps/v1beta2/namespaces/my-namespace/deployments/my-deployment", {
            "group": "apps",
            "apiversion": "v1beta2",
            "namespace": "my-namespace",
            "resourcetype": "deployments",
            "name": "my-deployment",
        }),
        ("/apis/apps/v1beta2/namespaces/my-namespace/deployments/my-deployment/status", {
            "group": "apps",
            "apiversion": "v1beta2",
            "namespace": "my-namespace",
            "resourcetype": "deployments",
            "name": "my-deployment",
            "subresource": "status"
        }),
        ("/apis/admissionregistration.k8s.io/v1/mutatingwebhookconfigurations/my-webhook", {
            "group": "admissionregistration.k8s.io",
            "apiversion": "v1",
            "resourcetype": "mutatingwebhookconfigurations",
            "name": "my-webhook"
        }),
        ("/apis/airspot.krules.dev/v1/mycrd/my-resource/status", {
            "group": "airspot.krules.dev",
            "apiversion": "v1",
            "resourcetype": "mycrd",
            "name": "my-resource",
            "subresource": "status"
        }),
        ("/api/v1/namespaces/my-namespace/pods/my-pod", {
            "apiversion": "v1",
            "namespace": "my-namespace",
            "resourcetype": "pods",
            "name": "my-pod"
        }),
        ("/api/v1/namespaces/my-namespace/pods/my-pod/status", {
            "group": "core",
            "apiversion": "v1",
            "namespace": "my-namespace",
            "resourcetype": "pods",
            "name": "my-pod",
            "subresource": "status"
        }),
        ("/api/v1/nodes/my-node-1234", {
            "group": "core",
            "apiversion": "v1",
            "resourcetype": "nodes",
            "name": "my-node-1234"
        }),
        ("/api/v1/nodes/my-node-1234/status", {
            "group": "core",
            "apiversion": "v1",
            "resourcetype": "nodes",
            "name": "my-node-1234",
            "subresource": "status"
        }),
        ("/api/v1/namespaces/my-namespace", {
            "group": "core",
            "apiversion": "v1",
            "resourcetype": "namespaces",
            "name": "my-namespace",
        }),
        ("/api/v1/namespaces/my-namespace/status", {
            "group": "core",
            "apiversion": "v1",
            "resourcetype": "namespaces",
            "name": "my-namespace",
            "subresource": "status"
        })
    ]

    for ep, values in endpoints:
            props, ext_props = subject_storage_factory(ep, {}).load()

            if "group" in values:
                assert ext_props["group"] == values["group"]
            assert ext_props["apiversion"] == values["apiversion"]
            if "namespace" in values:
                assert ext_props["namespace"] == values["namespace"]
            assert ext_props["resourcetype"] == values["resourcetype"]
            if "subresource" in values:
                assert ext_props["subresource"] == values["subresource"]
            assert ext_props["name"] == values["name"]


def test_load_store_and_flush():

    global NAMESPACE, POD_NAME
    spod = subject_storage_factory(f"/api/v1/namespaces/{NAMESPACE}/pods/{POD_NAME}")
    props, ext_props = spod.load()

    initial_len_props = len(props)
    initial_len_ext_props = len(ext_props)

    spod.store(
        inserts=(
            SubjectProperty("p1", 1),
            SubjectProperty("p2", "2'3"),
            SubjectExtProperty("px1", 3),
            SubjectExtProperty("p1", "s1")
        )
    )

    spod._resource_body = None
    props, ext_props = spod.load()

    assert len(props) == 2+initial_len_props
    assert len(ext_props) == 2+initial_len_ext_props
    assert props["p1"] == 1
    assert props["p2"] == "2'3"
    assert ext_props["px1"] == 3
    assert ext_props["p1"] == "s1"

    spod.store(
        updates=(
            SubjectProperty("p2", 3),
            SubjectExtProperty("p1", "s2"),
        ),
        deletes=(
            SubjectProperty("p1"),
            SubjectExtProperty("px1"),
        )
    )

    spod._resource_body = None
    props, ext_props = spod.load()

    assert len(props) == 1+initial_len_props
    assert len(ext_props) == 1+initial_len_ext_props
    assert props["p2"] == 3
    assert ext_props["p1"] == "s2"

    spod.flush()

    props, ext_props = spod.load()

    assert len(props) == initial_len_props and len(ext_props) == initial_len_ext_props


def test_set_and_get():

    global NAMESPACE, POD_NAME
    spod = subject_storage_factory(f"/api/v1/namespaces/{NAMESPACE}/pods/{POD_NAME}")

    with pytest.raises(AttributeError):
        spod.get(SubjectProperty("pset"))

    # simple value
    new_value, old_value = spod.set(SubjectProperty("pset", 1))
    assert old_value is None
    assert new_value == 1
    assert spod.get(SubjectProperty("pset")) == 1

    spod.delete(SubjectProperty("pset"))
    new_value, old_value = spod.set(SubjectProperty("pset", 1), 0)
    assert old_value == 0
    assert new_value == 1
    new_value, old_value = spod.set(SubjectProperty("pset", "1'2"))
    assert new_value == "1'2"
    assert old_value == 1
    assert spod.get(SubjectProperty("pset")) == "1'2"

    # computed value
    spod.set(SubjectProperty("pset", lambda: "1'2"))  # no args
    spod.set(SubjectProperty("pset", lambda x: x.replace("'", "$")))
    assert spod.get(SubjectProperty("pset")) == "1$2"


def test_ext_props():

    global NAMESPACE, POD_NAME
    spod = subject_storage_factory(f"/api/v1/namespaces/{NAMESPACE}/pods/{POD_NAME}")

    spod.flush()

    initial_len = len(spod.get_ext_props())

    spod.set(SubjectProperty("p1", 1))
    spod.set(SubjectProperty("p2", 2))
    spod.set(SubjectExtProperty("p3", 3))
    spod.set(SubjectExtProperty("p4", 4))

    props = spod.get_ext_props()
    assert len(props) == 2+initial_len

    assert "p3" in props and props["p3"] == 3
    assert "p4" in props and props["p4"] == 4
