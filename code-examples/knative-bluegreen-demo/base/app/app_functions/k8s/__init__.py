import pykube
from krules_core.base_functions import RuleFunctionBase
from krules_core.providers import subject_factory
import json


def k8s_subject(obj):
    return subject_factory("k8s:{}".format(obj["metadata"]["selfLink"]), event_data=obj)


class K8sObjectCreate(RuleFunctionBase):

    def execute(self, obj):

        api = self.payload.get("_k8s_api_client")
        if api is None:
            config = pykube.KubeConfig.from_service_account()
            api = pykube.HTTPClient(config)
            # self.payload["_k8s_api_client"] = api

        apiversion = obj.get("apiVersion")
        kind = obj.get("kind")
        pykube.object_factory(api, apiversion, kind)(api, obj).create()


class K8sObjectsQuery(RuleFunctionBase):

    def execute(self, apiversion=None, kind=None, filters={}, foreach=None, returns=None):

        api = self.payload.get("_k8s_api_client")
        if api is None:
            config = pykube.KubeConfig.from_service_account()
            api = pykube.HTTPClient(config)
            # self.payload["_k8s_api_client"] = api

        if apiversion is None:
            apiversion = self.subject.get_ext("apiversion")
            if "group" in self.subject.get_ext_props():
                apiversion = "{}/{}".format(self.subject.get_ext("group"), apiversion)
        if kind is None:
            kind = self.subject.get_ext("kind")
        obj = pykube.object_factory(api, apiversion, kind)
        if "namespace" not in filters:
            filters.update({
                "namespace": self.subject.get_ext("namespace")
            })
        qobjs = obj.objects(api).filter(**filters)

        if foreach is not None:
            for obj in qobjs:
                foreach(obj)

        if returns is not None:
            return returns(qobjs)
        return len(qobjs)


class K8sObjectUpdate(RuleFunctionBase):

    def execute(self, func, subresource=None, name=None, apiversion=None, kind=None, filters={}):

        api = self.payload.get("_k8s_api_client")
        if api is None:
            config = pykube.KubeConfig.from_service_account()
            api = pykube.HTTPClient(config)
            self.payload["_k8s_api_client"] = api

        use_context = subresource is None and name is None and apiversion is None and kind is None and len(filters) == 0
        context = self.payload
        if use_context and context.get("metadata", {}).get("name") is None:
            resp = api.session.get(url=f"{api.url}{self.subject.name[len('k8s:'):]}")
            resp.raise_for_status()
            context = resp.json()

        if use_context:
            apiversion = context["apiVersion"]
            kind = context["kind"]
            name = context["metadata"]["name"]
        #     namespace = context["metadata"]["namespace"]
        # else:
        #     namespace = self.subject.get_ext("namespace")

        factory = pykube.object_factory(api, apiversion, kind)
        # if "namespace" not in filters:
        #     filters.update({
        #         "namespace": self.subject.get_ext("namespace")
        #     })
        # obj.update() might fail if the resource was modified between loading and updating. In this case you need to retry.
        # Reference: https://pykube.readthedocs.io/en/latest/howtos/update-deployment-image.html
        while True:
            obj = factory.objects(api).filter(**filters).get(name=name)

            func(obj.obj)
            try:
                obj.update(subresource=subresource)
                break
            except pykube.exceptions.HTTPError as ex:
                print(str(ex))
                if ex.code == 409:
                    continue
                else:
                    raise ex


class K8sObjectDelete(RuleFunctionBase):

    def execute(self, subresource=None, name=None, apiversion=None, kind=None, filters={}):

        api = self.payload.get("_k8s_api_client")
        if api is None:
            config = pykube.KubeConfig.from_service_account()
            api = pykube.HTTPClient(config)
            self.payload["_k8s_api_client"] = api

        use_context = subresource is None and name is None and apiversion is None and kind is None and len(filters) == 0
        context = self.payload
        if use_context and context.get("metadata", {}).get("name") is None:
            resp = api.session.get(url=f"{api.url}{self.subject.name[len('k8s:'):]}")
            resp.raise_for_status()
            context = resp.json()

        if use_context:
            apiversion = context["apiVersion"]
            kind = context["kind"]
            name = context["metadata"]["name"]
        #     namespace = context["metadata"]["namespace"]
        # else:
        #     namespace = self.subject.get_ext("namespace")

        factory = pykube.object_factory(api, apiversion, kind)
        # if "namespace" not in filters:
        #     filters.update({
        #         "namespace": self.subject.get_ext("namespace")
        #     })
        # obj.update() might fail if the resource was modified between loading and updating. In this case you need to retry.
        # Reference: https://pykube.readthedocs.io/en/latest/howtos/update-deployment-image.html
        factory.objects(api).filter(**filters).get(name=name).delete()

