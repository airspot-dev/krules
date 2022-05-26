import copy
import os
import time
import typing
from socket import gethostname

import yaml

from features import update_features_labels
from k8s_functions import *
from krules_core import RuleConst as Const
from krules_core.base_functions import *
from krules_core.event_types import SUBJECT_PROPERTY_CHANGED

from cfgp import _hashed, apply_configuration, check_applies_to

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING


# TODO: move in k8s_functions
class SetK8sObjectPropertyAnnotation(RuleFunctionBase):
    """
    Act as a reactive property but using object annotations
    Subject is "k8s:<apiVersions>:<kind>:<name>"
    An 'object' field is added having the resource definition
    Notice that the resource is altered in the received dict object but not actually committed
    you must ensure that the resource is updated
    """

    def execute(self,
                obj: typing.Union[dict, typing.Callable],
                property_name: typing.Union[str, typing.Callable],
                value: typing.Union[str, typing.Callable]):

        metadata = obj.setdefault("metadata", {})
        annotations = metadata.setdefault("annotations", {})

        props = yaml.load(
            annotations.setdefault("krules.dev/props", "{}"),
            Loader=yaml.SafeLoader
        )

        old_value = props.get(property_name)

        if callable(value):
            value = value(old_value)

        if old_value != value:
            props[property_name] = value
            annotations["krules.dev/props"] = yaml.dump(props, Dumper=yaml.SafeDumper)

            self.router.route(
                event_type=SUBJECT_PROPERTY_CHANGED,
                subject=self.subject,
                payload={
                    "property_name": property_name,
                    "value": value,
                    "old_value": old_value,
                    "object": obj
                }
            )


class K8sObjectPatchAnnotations(K8sObjectUpdate):

    def execute(self, **kwargs):

        obj = self.payload["request"]["object"]
        old_obj = self.payload["request"]["oldObject"]

        if old_obj is not None and \
            old_obj.get("metadata", {}).get("annotations", {}) != obj.get("metadata", {}).get("annotations", {}):

            patch = {
                "metadata": {
                    "annotations": obj.get("metadata", {}).get("annotations", {})
                }
            }

            super().execute(patch=patch,
                            name=obj["metadata"]["name"],
                            apiversion=obj["apiVersion"],
                            kind=obj["kind"],
                            namespace=obj["metadata"]["namespace"])


class CreateConfigMap(K8sObjectCreate):

    def execute(self, name: typing.Union[str, typing.Callable], provider: typing.Union[dict, typing.Callable],
                **kwargs):
        data = provider["spec"].get("data", {})
        provider_name = provider["metadata"]["name"]
        namespace = provider["metadata"]["namespace"]
        cm_name = name
        cm = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": cm_name,
                "namespace": namespace,
                "labels": {
                    "config.krules.dev/provider": provider_name,
                },
            },
            "data": {
                "{}.yaml".format(cm_name.replace("-", "_")): yaml.dump(data)
            }
        }

        super().execute(cm)


class ApplyConfigurationToExistingResources(K8sObjectsQuery):


    def _apply_configuration_wrapper(self, configuration, obj, root_expr, preserve_name):

        _log = self.payload["__log"] = []

        labels = obj.obj.get("metadata", {}).get("labels", {})

        features_labels = update_features_labels(configuration, obj.obj)
        _log.append({
            "cfgp": configuration.get("metadata").get("name"),
            "features_labels": features_labels
        })
        if len(features_labels):
            api = self.get_api_client()
            for feature_lbl in features_labels:
                prefix, name = feature_lbl.split("/")
                selector = {
                    f"{prefix[len('features.'):]}/provides-feature": name,
                }
                _log.append({
                    "selector": selector
                })
                cfgps = ConfigurationProvider.objects(api).filter(
                    namespace=obj.obj.get("metadata").get("namespace"),
                    selector=selector
                )
                for cfgp in cfgps:
                    _log.append({
                        "found": cfgp.name
                    })
                    appliesTo = cfgp.obj.get("spec").get("appliesTo")
                    if check_applies_to(appliesTo, labels):
                        apply_configuration(cfgp.obj, dest=obj.obj, root_expr=root_expr, preserve_name=preserve_name,
                                            _log=_log)

        apply_configuration(configuration, obj.obj, root_expr=root_expr, preserve_name=preserve_name,
                            _log=self.payload["__log"])

        try:
            self.payload["__log"].append(
                ("before_update", obj.obj)
            )
            obj.update(is_strategic=False)
        except pykube.exceptions.HTTPError as ex:

            k8s_event_create(
                api=self.payload.get("_k8s_api_client"),
                producer=configuration["metadata"]["name"],
                involved_object={
                    "apiVersion": obj.api_kwargs()["version"],
                    "kind": obj.kind,
                    "metadata": {
                        "namespace": obj.namespace,
                        "name": obj.name,
                        "resourceVersion": obj.obj["metadata"]["resourceVersion"],
                        "uid": obj.obj["metadata"]["uid"]
                    }
                },
                action="ApplyConfiguration",
                message=str(ex),
                reason="FailedToApplyConfigurationProvider",
                type="Warning",
                reporting_component=os.environ.get("CE_SOURCE", gethostname()),
                reporting_instance=self.rule_name,
                source_component=configuration["metadata"]["name"],
            )

            raise ex

    def execute(self,
                configuration: typing.Union[dict, typing.Callable],
                apiversion: str,
                kind: str,
                root_expr: str,
                preserve_name: bool,
                filter_function: typing.Callable,
                **kwargs):

        configuration = copy.deepcopy(configuration)

        selector = {}
        for k, v in configuration["spec"].get("appliesTo", {}).items():
            if isinstance(v, type([])):
                selector[f"{k}__in"] = set(v)
            else:
                selector[k] = v


        super().execute(
            apiversion=apiversion, kind=kind,
            namespace=configuration["metadata"]["namespace"],
            selector=selector,
            foreach=lambda obj: (
                filter_function(obj) and (
                    self._apply_configuration_wrapper(
                        configuration, obj, root_expr=root_expr, preserve_name=preserve_name,
                    ),
                )
            )
        )


apply_configuration_rulesdata = [
    """
    On configuration change inject configuration to existing deployments
    """,
    {
        rulename: "cfgp-on-change-update-deployments",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("cfgp_hash"),
            ],
            processing: [
                ApplyConfigurationToExistingResources(
                    configuration=lambda payload: payload["object"],
                    apiversion="apps/v1",
                    kind="Deployment",
                    root_expr="$.spec.template",
                    preserve_name=True,
                    filter_function=lambda obj: len(obj.obj["metadata"].get("ownerReferences", [])) == 0,
                ),
            ]
        }
    },
    """
    On configuration change inject configuration to existing knative services
    """,
    {
        rulename: "cfgp-on-change-update-kservices",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("cfgp_hash"),
            ],
            processing: [
                ApplyConfigurationToExistingResources(
                    configuration=lambda payload: payload["object"],
                    apiversion="serving.knative.dev/v1",
                    kind="Service",
                    root_expr="$.spec.template",
                    preserve_name=False,
                    filter_function=lambda obj: True,
                ),
            ]
        }
    },

]


create_configuration_rulesdata = [
    """
    Annotate properties to react
    """,
    {
        rulename: "cfgp-annotate",
        subscribe_to: [
            "validate-configurationprovider-create",
            "validate-configurationprovider-update",
        ],
        ruledata: {
            processing: [
                SetK8sObjectPropertyAnnotation(
                    obj=lambda payload: payload["request"]["object"],
                    property_name="cfgp_hash",
                    value=lambda payload: "{}-{}".format(
                        payload["request"]["object"]["metadata"]["name"],
                        _hashed(
                            payload["request"]["object"]["spec"].get("data", {}),
                            payload["request"]["object"]["spec"].get("container", {}),
                            payload["request"]["object"]["spec"].get("volumes", {}),
                            # PLAYGROUND
                            payload["request"]["object"]["spec"].get("extensions", {}).get("features")
                        )
                    )
                ),
                SetK8sObjectPropertyAnnotation(
                    obj=lambda payload: payload["request"]["object"],
                    property_name="cm_name",
                    value=lambda payload: "{}-{}".format(
                        payload["request"]["object"]["metadata"]["name"],
                        _hashed(
                            payload["request"]["object"]["spec"].get("data", {}),
                        )
                    )
                ),
                K8sObjectPatchAnnotations()
                # TODO: update status subresource
            ]
        }
    },
    """
    On new configmap (name) create it
    """,
    {
        rulename: "cfgp-create-cm",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("cm_name"),
                K8sObjectsQuery(  # cm does not already exists
                    apiversion="v1", kind="ConfigMap",
                    returns=lambda payload: (
                        lambda qobjs: qobjs.get_or_none(name=payload["value"]) is None
                    )
                )
            ],
            processing: [
                CreateConfigMap(
                    name=lambda payload: payload["value"],
                    provider=lambda payload: payload["object"]
                ),
            ]
        }
    },
    """
    On new configmap (name) remove the old one
    """,
    {
        rulename: "cfgp-cm-remove-old",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("cm_name", old_value=lambda v: v is not None),
            ],
            processing: [
                K8sObjectDelete(
                    apiversion="v1", kind="ConfigMap",
                    namespace=lambda payload: payload["object"]["metadata"].get("namespace"),
                    name=lambda payload: payload["old_value"]
                )
            ]
        }
    },
    """
    On generated config map deleted force the creation of a new one
    """,
    {
        rulename: "cfgp-cm-on-remove-recreate",
        subscribe_to: "validate-configmap-delete",
        ruledata: {
            filters: [
                PayloadMatchOne('request.oldObject.metadata.labels."config.krules.dev/provider"',
                                payload_dest="provider_name"),
                Filter(
                    # ensure we have an updated version
                    lambda: time.sleep(10) or True
                ),
                K8sObjectsQuery(
                    apiversion="krules.dev/v1alpha1",
                    kind="ConfigurationProvider",
                    namespace=lambda payload: payload["request"]["namespace"],
                    returns=lambda payload: lambda qobjs: (
                        payload.setdefault("provider_object", qobjs.get(name=payload["provider_name"]).obj)
                        and yaml.load(
                            payload["provider_object"]["metadata"]["annotations"]["krules.dev/props"],
                            Loader=yaml.SafeLoader,
                        )["cm_name"] == payload["request"]["oldObject"]["metadata"]["name"]
                    )
                ),
            ],
            processing: [
                CreateConfigMap(
                    name=lambda payload: payload["request"]["oldObject"]["metadata"]["name"],
                    provider=lambda payload: payload.get("provider_object"),
                )
            ]
        }
    },
    """
    On delete cfgp remove cm
    """,
    {
        rulename: "cfgp-on-delete-remove-cm",
        subscribe_to: "validate-configurationprovider-delete",
        ruledata: {
            processing: [
                K8sObjectDelete(
                    apiversion="v1", kind="ConfigMap",
                    namespace=lambda payload: payload["request"]["namespace"],
                    name=lambda payload: (
                        yaml.load(
                            payload["request"]["oldObject"]["metadata"].get("annotations", {}).get("krules.dev/props"),
                            Loader=yaml.SafeLoader,
                        )["cm_name"]
                    )
                )
            ]
        }
    }
]


rulesdata = create_configuration_rulesdata + apply_configuration_rulesdata