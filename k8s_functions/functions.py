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
import inspect

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

        if "namespace" not in filters and "namespace" in self.subject.get_ext_props() \
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

        if "namespace" not in filters and "namespace" in self.subject.get_ext_props() \
                and self.subject.ext_namespace is not None:
            filters.update({
                "namespace": self.subject.get_ext("namespace")
            })

        obj = obj.objects(self.payload.get("_k8s_api_client")).filter(**filters).get(name=name)

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


class K8sObjectCreate(K8sRuleFunctionBase):

    def execute(self, obj):

        apiversion = obj.get("apiVersion")
        kind = obj.get("kind")
        while True:
            try:
                self._get_object(apiversion, kind)(self.payload.get("_k8s_api_client"), obj).create()
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
