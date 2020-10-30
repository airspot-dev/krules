import operator

import os
import pykube
import pytest
import rx
from dependency_injector import providers
from k8s_subjects_storage import storage_impl as k8s_storage_impl
from krules_core.base_functions import IsTrue

from krules_core.core import RuleFactory
from krules_core import RuleConst
from krules_core.providers import event_router_factory, subject_storage_factory, proc_events_rx_factory
from krules_core.tests.subject.sqlite_storage import SQLLiteSubjectStorage

from .functions import (
    K8sObjectCreate,
    K8sObjectUpdate,
    K8sObjectsQuery,
    K8sObjectDelete, k8s_subject
)

Filter = Process = IsTrue

def setup_module(_):

    extra_kwargs = {}
    if os.environ.get("API_URL", False):
        extra_kwargs.update({
            "override_api_url": os.environ.get("API_URL")
        })

    subject_storage_factory.override(
        providers.Factory(
            lambda name, event_info, event_data: (
                name.startswith("k8s:") and k8s_storage_impl.SubjectsK8sStorage(
                    resource_path=name[4:],
                    resource_body=event_data.get("k8s_object"))
                or providers.Factory(lambda *args, **kwargs: SQLLiteSubjectStorage(args[0], ":memory:"))
            )
        )
    )

    proc_events_rx_factory.override(providers.Singleton(rx.subjects.ReplaySubject))


def teardown_module(_):
    subject_storage_factory.reset_last_overriding()

@pytest.fixture
def api():
    if os.environ.get("API_URL", False):
        config = pykube.KubeConfig.from_url(os.environ.get("API_URL"))
    else:
        config = pykube.KubeConfig.from_env()
    return pykube.HTTPClient(config)

@pytest.fixture
def namespace(api):
    if os.environ.get("NAMESPACE", False):
        return os.environ.get("NAMESPACE")
    return api.config.namespace

def _assert(expr, msg="test failed"):
    assert expr, msg
    return True

def test_create(api, namespace):


    RuleFactory.create(
        'test-k8s-create',
        subscribe_to="test-create",
        data={
            RuleConst.PROCESSING: [
                K8sObjectCreate({
                    "apiVersion": "v1",
                    "kind": "Pod",
                    "metadata": {
                        "name": "test-pod-1",
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
                }),
                K8sObjectCreate({
                    "apiVersion": "v1",
                    "kind": "Pod",
                    "metadata": {
                        "name": "test-pod-2",
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
                })
            ]
        }
    )

    proc_events_rx_factory().subscribe(
        lambda x: x[RuleConst.RULENAME] == 'test-k8s-create' and
                  _assert(
                      not x[RuleConst.GOT_ERRORS] and x[RuleConst.PROCESSED],
                      "test-k8s-create proc failed"
                  )
    )

    event_router_factory().route("test-create", "some", {})


    pykube.Pod.objects(api).filter(namespace=namespace)
    objs = pykube.Pod.objects(api).filter(namespace=namespace, selector={"app": "pytest-temp"})
    # wait for pods ready
    watch = objs.watch()
    ready = 0
    for ev in watch:
        print(ev.type, ev.object.name, ev.object.ready)
        if ev.object.ready:
            ready += 1
        if ready == 2:
            break
    assert len(objs) == 2

    event_router_factory().unregister_all()


def test_update(api, namespace):

    RuleFactory.create(
        'test-k8s-update-in-context',
        subscribe_to="test-update-in-context",
        data={
            RuleConst.PROCESSING: [
                # update from subject
                K8sObjectUpdate(
                    lambda obj: (
                        obj["metadata"]["labels"].update({
                            "updated": "pod-1"
                        })
                    )
                ),
            ]
        }
    )

    proc_events_rx_factory().subscribe(
        lambda x: x[RuleConst.RULENAME] == 'test-k8s-update-in-context' and
                  _assert(
                      x[RuleConst.PROCESSED] and x[RuleConst.GOT_ERRORS] is False,
                      "test-k8s-update-in-context proc failed"
                  )
    )

    objs = pykube.Pod.objects(api).filter(namespace=namespace, selector={"app": "pytest-temp"})
    watch = objs.watch().filter(field_selector={"metadata.name": "test-pod-1"})
    event_router_factory().route(
        "test-update-in-context",
        f"k8s:/api/v1/namespaces/{namespace}/pods/test-pod-1", {}
    )

    try:
        for ev in watch:
            if ev.type == 'ADDED' and ev.object.obj["metadata"]["labels"]["updated"] == "pod-1":
                break
    except:
        assert False, "update pod-1 event failed"

    RuleFactory.create(
        'test-k8s-update-off-context',
        subscribe_to="test-update-off-context",
        data={
            RuleConst.PROCESSING: [
                # update from subject
                K8sObjectUpdate(
                    lambda obj: (
                        obj["metadata"]["labels"].update({
                            "updated": "pod-2"
                        })
                    ),
                    name="test-pod-2",
                    apiversion="v1",
                    kind="Pod",
                    namespace=namespace
                ),
            ]
        }
    )

    proc_events_rx_factory().subscribe(
        lambda x: x[RuleConst.RULENAME] == 'test-k8s-update-off-context' and
                  _assert(
                      x[RuleConst.GOT_ERRORS] is False and x[RuleConst.PROCESSED],
                      "test-k8s-update-off-context proc failed"
                  )
    )

    objs = pykube.Pod.objects(api).filter(namespace=namespace, selector={"app": "pytest-temp"})
    watch = objs.watch().filter(field_selector={"metadata.name": "test-pod-2"})
    event_router_factory().route(
        "test-update-off-context",
        "none", {}
    )

    try:
        for ev in watch:
            if ev.type == 'ADDED' and ev.object.obj["metadata"]["labels"]["updated"] == "pod-2":
                break
    except:
        assert False, "update pod-2 event failed"

    event_router_factory().unregister_all()


def tests_query_foreach(api, namespace):

    RuleFactory.create(
        'test-k8s-query-foreach',
        subscribe_to="test-query-foreach",
        data={
            RuleConst.PROCESSING: [
                K8sObjectsQuery(
                    foreach=lambda obj: (
                        obj.obj["metadata"]["labels"].update({
                            "updated": "foreach"
                        }),
                        obj.update()
                    ),
                    apiversion="v1",
                    kind="Pod",
                    namespace=namespace,
                    selector={
                        "app": "pytest-temp"
                    }
                ),
            ]
        }
    )

    proc_events_rx_factory().subscribe(
        lambda x: x[RuleConst.RULENAME] == 'test-k8s-query-foreach' and
                  _assert(
                      x[RuleConst.GOT_ERRORS] is False and x[RuleConst.PROCESSED],
                      "test-k8s-query-foreach proc failed"
                  )
    )

    watch = pykube.Pod.objects(api).filter(namespace=namespace, selector={"app": "pytest-temp"}).watch()
    event_router_factory().route(
        "test-query-foreach",
        "none", {}
    )

    try:
        updated = 0
        for ev in watch:
            if ev.type == 'ADDED' and ev.object.obj["metadata"]["labels"]["updated"] == "foreach":
                updated += 1
            if updated == 2:
                break
    except:
        assert False, "query update event failed"

    assert updated == 2

    event_router_factory().unregister_all()

#@pytest.mark.skip
def test_k8s_subject(api, namespace):

    RuleFactory.create(
        'test-k8s-subject',
        subscribe_to='test-k8s-subject',
        data={
            RuleConst.FILTERS: [
                Filter(
                    lambda: (
                        k8s_subject(resource_path=f"/api/v1/namespaces/{namespace}/pods/test-pod-1").ext_name == "test-pod-1"
                    )
                ),
                Filter(
                    K8sObjectsQuery(
                        returns=lambda obj: (
                            k8s_subject(obj).ext_name == "test-pod-1"
                        )
                    )
                ),
                Filter(
                    K8sObjectsQuery(
                        returns=lambda obj: (
                                k8s_subject(obj.obj).ext_name == "test-pod-1"
                        )
                    )
                )
            ],
            RuleConst.PROCESSING: [
                Process(True)
            ]
        }
    )

    proc_events_rx_factory().subscribe(
        lambda x: x[RuleConst.RULENAME] == 'test-k8s-subject' and
                  _assert(
                      x[RuleConst.GOT_ERRORS] is False and x[RuleConst.PROCESSED],
                      "test-k8s-subject proc failed"
                  )
    )

    event_router_factory().route(
        "test-k8s-subject",
        f"k8s:/api/v1/namespaces/{namespace}/pods/test-pod-1", {}
    )



# NOTE: delete tests K8SObjectsQuery#returns indirectly
def test_delete(api, namespace):

    RuleFactory.create(
        'test-k8s-delete-in-context',
        subscribe_to="test-delete-in-context",
        data={
            RuleConst.PROCESSING: [
                # update from subject
                K8sObjectDelete()
            ]
        }
    )

    objs = pykube.Pod.objects(api).filter(namespace=namespace, selector={"app": "pytest-temp"})
    watch = objs.watch().filter(field_selector={"metadata.name": "test-pod-1"})
    proc_events_rx_factory().subscribe(
        lambda x: x[RuleConst.RULENAME] == 'test-k8s-delete-in-context' and
                  _assert(
                      x[RuleConst.GOT_ERRORS] is False and x[RuleConst.PROCESSED],
                      "test-k8s-delete-in-context proc failed"
                  )
    )
    event_router_factory().route(
        "test-delete-in-context",
        f"k8s:/api/v1/namespaces/{namespace}/pods/test-pod-1", {}
    )

    for ev in watch:
        if ev.type == "DELETED":
            break
    assert len(objs) == 1

    RuleFactory.create(
        'test-k8s-delete-off-context',
        subscribe_to="test-delete-off-context",
        data={
            RuleConst.PROCESSING: [
                # update from subject
                K8sObjectDelete(
                    name="test-pod-2",
                    apiversion="v1",
                    kind="Pod",
                    namespace=namespace
                )
            ]
        }
    )

    objs = pykube.Pod.objects(api).filter(namespace=namespace, selector={"app": "pytest-temp"})
    watch = objs.watch().filter(field_selector={"metadata.name": "test-pod-2"})
    proc_events_rx_factory().subscribe(
        lambda x: x[RuleConst.RULENAME] == 'test-k8s-delete-off-context' and
                  _assert(
                      x[RuleConst.GOT_ERRORS] is False and x[RuleConst.PROCESSED],
                      "test-k8s-delete-off-context proc failed"
                  )
    )
    event_router_factory().route(
        "test-delete-off-context",
        f"k8s:/api/v1/namespaces/{namespace}", {}
    )

    for ev in watch:
        if ev.type == "DELETED":
            break
    assert len(objs) == 0

    event_router_factory().unregister_all()



