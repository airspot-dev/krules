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
from datetime import datetime, timezone
import inspect
import uuid

import pykube
from krules_core.base_functions import RuleFunctionBase

from krules_core.providers import subject_factory


def k8s_subject(obj=None, resource_path=None, prefix="k8s:"):
    """
    Returns a k8s subject instance providing a kubernetes resource
    :param obj:
    :param resource_path:
    :param prefix:
    :return:
    """
    if hasattr(obj, 'obj'):
        obj = obj.obj
    if obj is None:
        obj = {}
    if resource_path is None:
        resource_path = obj["metadata"]["selfLink"]
    return subject_factory(f"{prefix}{resource_path}", event_data=obj)


def k8s_object(subject, renew=False):
    """
    Returns the k8s resource providing a subject instance
    :param subject:
    :return:
    """
    try:
        if renew:
            subject._storage._reset()
        return subject._storage._get_resource()
    except AttributeError:
        raise TypeError("not a k8s storaged subject")


def k8s_event_create(api, producer, action, message, reason, type,
                     reporting_component=None, reporting_instance=None, involved_object=None, namespace=None,
                     source_component=None, first_timestamp=None, last_timestamp=None):

    dt_now = datetime.now(timezone.utc).astimezone().isoformat()

    if first_timestamp is None:
        first_timestamp = dt_now
    if last_timestamp is None:
        last_timestamp = dt_now

    obj = {
        "apiVersion": "v1",
        "kind": "Event",
        "eventTime": datetime.now(timezone.utc).astimezone().isoformat(),
        "firstTimestamp": first_timestamp,
        "lastTimestamp": last_timestamp,
        "metadata": {
            "name": "{}.{}".format(producer, uuid.uuid4().hex[:16])
        },
        "action": action,
        "message": message,
        "reason": reason,
        # "source": {
        #     "component": source_component,
        # },
        "type": type
    }

    if reporting_component:
        obj.update({
            "reportingComponent": reporting_component
        })
    if reporting_instance:
        obj.update({
            "reportingInstance": reporting_instance
        })
    if source_component:
        obj.update({
            "source": {
                "component": source_component
            }
        })

    namespace = namespace is not None and namespace \
                or involved_object is not None and involved_object.get("metadata", {}).get("namespace") \
                or None
    if namespace:
        obj["metadata"].update({
            "namespace": namespace
        })

    if involved_object:
        obj.update({
            "involvedObject": {
                "apiVersion": involved_object.get("apiVersion"),
                "kind": involved_object.get("kind"),
                "name": involved_object.get("metadata").get("name"),
                "namespace": involved_object.get("metadata").get("namespace"),
                "resourceVersion": involved_object.get("metadata").get("resourceVersion"),
                "uid": involved_object.get("metadata").get("uid")
            },
        })

    pykube.Event(api, obj).create()


class K8sRuleFunctionBase(RuleFunctionBase):

    def _get_object(self, apiversion, kind):

        api = self.payload.get("_k8s_api_client")
        if api is None:
            config = pykube.KubeConfig.from_env()
            api = pykube.HTTPClient(config)
            self.payload["_k8s_api_client"] = api

        if apiversion is None and "apiversion" in self.subject.get_ext_props():
            apiversion = self.subject.get_ext("apiversion")

        if kind is None and "kind" in self.subject.get_ext_props():
            kind = self.subject.get_ext("kind")

        return pykube.object_factory(api, apiversion, kind)


class K8sObjectsQuery(K8sRuleFunctionBase):

    def execute(self, apiversion=None, kind=None, foreach=None, returns=None, **filters):

        obj = self._get_object(apiversion, kind)

        # we are implicitly referring to the resource in the subject
        if kind is None and apiversion is None \
                and "namespace" not in filters \
                and "namespace" in self.subject.get_ext_props() \
                and self.subject.ext_namespace is not None:
            filters.update({
                "namespace": self.subject.get_ext("namespace")
            })

        qobjs = obj.objects(self.payload.get("_k8s_api_client")).filter(**filters)

        if foreach is not None:
            for obj in qobjs:
                while True:
                    try:
                        foreach(obj)
                        break
                    except pykube.exceptions.HTTPError as ex:
                        if ex.code == 409:
                            continue
                        else:
                            raise ex

        if returns is not None:
            while True:
                try:
                    return returns(qobjs)
                except pykube.exceptions.HTTPError as ex:
                    if ex.code == 409:
                        continue
                    else:
                        raise ex
        return len(qobjs)


class K8sObjectUpdate(K8sRuleFunctionBase):

    def execute(self, patch, name=None, apiversion=None, kind=None, subresource=None, is_strategic=True, **filters):

        if name is None:
            name = self.subject.get_ext("name")

        obj = self._get_object(apiversion, kind)

        # we are implicitly referring to the resource in the subject
        if kind is None and apiversion is None \
                and "namespace" not in filters \
                and "namespace" in self.subject.get_ext_props() \
                and self.subject.ext_namespace is not None:
            filters.update({
                "namespace": self.subject.get_ext("namespace")
            })

        obj = obj.objects(self.payload.get("_k8s_api_client")).filter(**filters).get(name=name)

        # retrocompatibility
        if inspect.isfunction(patch):
            patch(obj.obj)
        else:
            obj.obj.update(patch)

        while True:
            try:
                obj.update(subresource=subresource, is_strategic=is_strategic)
                break
            except pykube.exceptions.HTTPError as ex:
                if ex.code == 409:
                    continue
                else:
                    raise ex


class K8sObjectPatch(K8sRuleFunctionBase):

    def execute(self, patch, name=None, apiversion=None, kind=None, subresource=None, **filters):

        if name is None:
            name = self.subject.get_ext("name")

        obj = self._get_object(apiversion, kind)

        # we are implicitly referring to the resource in the subject
        if kind is None and apiversion is None \
                and "namespace" not in filters \
                and "namespace" in self.subject.get_ext_props() \
                and self.subject.ext_namespace is not None:
            filters.update({
                "namespace": self.subject.get_ext("namespace")
            })

        obj = obj.objects(self.payload.get("_k8s_api_client")).filter(**filters).get(name=name)

        while True:
            try:
                obj.patch(patch, subresource=subresource)
                break
            except pykube.exceptions.HTTPError as ex:
                if ex.code == 409:
                    continue
                else:
                    raise ex


class K8sObjectCreate(K8sRuleFunctionBase):

    def execute(self, obj):

        apiversion = obj.get("apiVersion")
        kind = obj.get("kind")
        while True:
            try:
                obj_kind = self._get_object(apiversion, kind)
                api = self.payload.get("_k8s_api_client")
                obj_ref = obj_kind(api, obj)
                if not obj_ref.exists():
                    obj_ref.create()
                break
            except pykube.exceptions.HTTPError as ex:
                if ex.code == 409:
                    continue
                else:
                    raise ex


class K8sObjectDelete(K8sObjectsQuery):

    def execute(self, name=None, apiversion=None, kind=None, **filters):
        if name is None:
            name = self.subject.get_ext("name")

        super().execute(apiversion=apiversion, kind=kind, returns=lambda qobjs: (
            qobjs.get(name=name).delete()
        ), **filters)
