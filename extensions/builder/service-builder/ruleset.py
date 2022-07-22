import os
import uuid

from krules_core import RuleConst as Const
from krules_core.event_types import *
from builder_functions import *

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING
description = Const.DESCRIPTION

ruleset_config: dict = configs_factory()["rulesets"][os.environ["CE_SOURCE"]]


def _get_svc_ready_status(obj: dict):
    if obj.get("apiVersion").startswith("serving.knative.dev/"):
        for condition in obj.get("status", {}).get("conditions", []):
            if condition.get("type") == "Ready":
                return condition.get("status")
    elif obj.get("kind") == "Deployment":
        for condition in obj.get("status", {}).get("conditions", []):
            if condition.get("type") == "Available":
                return condition.get("status")

    return "Unknown"


def _get_svc_revision(obj: dict):
    if obj.get("apiVersion").startswith("serving.knative.dev/"):
        for revision in obj.get("status", {}).get("traffic", []):
            if revision.get("latestRevision"):
                return revision.get("revisionName")
    elif obj.get("kind") == "Deployment":
        return obj.get("metadata", {}).get("name")

    return "Unknown"


rulesdata = [
    {
        rulename: "set-props-on-k8s-subject",
        description: """
            Maintains a sync between the labels and annotated properties on the service kubernetes resources
            with his related subject
        """,
        subscribe_to: [
            "dev.knative.apiserver.resource.update",
            "dev.knative.apiserver.resource.add",
        ],
        ruledata: {
            filters: [
                IsDeployableTarget(
                    lambda payload: payload
                ),
            ],
            processing: [
                SetSubjectProperties(
                    subject=lambda subject: f"k8s:{subject.name}",
                    props=lambda payload: yaml.load(
                        payload["metadata"].get("annotations", {}).setdefault("krules.dev/props", "{}"),
                        Loader=yaml.SafeLoader
                    ),
                    use_cache=False,
                    unmuted="*"
                ),
                SetSubjectProperty(
                    subject=lambda subject: f"k8s:{subject.name}",
                    property_name="applied",
                    value=lambda payload: yaml.load(
                        payload["metadata"].get("annotations", {}).get("config.krules.dev/applied", "{}"),
                        Loader=yaml.SafeLoader
                    ),
                    use_cache=False,
                ),
                SetSubjectProperty(
                    subject=lambda subject: f"k8s:{subject.name}",
                    property_name="labels",
                    value=lambda payload: payload.get("metadata", {}).get("labels", {}),
                    use_cache=False,
                ),
                SetSubjectProperty(
                    subject=lambda subject: f"k8s:{subject.name}",
                    property_name="ready",
                    value=lambda payload: _get_svc_ready_status(payload),
                    use_cache=False,
                ),
                SetSubjectProperty(
                    subject=lambda subject: f"k8s:{subject.name}",
                    property_name="revision",
                    value=lambda payload: _get_svc_revision(payload),
                    use_cache=False,
                )
            ],
        }
    },
    {
        rulename: "flush-k8s-subject",
        description: """
            Flush the related subject when a kubernetes resource is deleted
        """,
        subscribe_to: [
            "dev.knative.apiserver.resource.delete",
        ],
        ruledata: {
            filters: [
                IsDeployableTarget(
                    resource=lambda payload: payload
                )
            ],
            processing: [
                Process(
                    lambda subject: subject_factory(f"k8s:{subject.name}").flush()
                )
            ],
        }
    },
    {
        rulename: "on-service-labels-update-set-build-source",
        description: """
            The build source is set when the service's labels changes (features added)
            or configuration updated. 
        """,
        subscribe_to: [
            SUBJECT_PROPERTY_CHANGED,
            #"forced-subject-property-changed",  # workaround in UpdateSubjectConfigurationProperty
            ],
        ruledata: {
            filters: [
                Filter(
                    lambda subject: subject.name.startswith("k8s:")
                ),
                Filter(
                    #lambda payload: payload["property_name"] in ["labels", "configuration"]
                    lambda payload: payload["property_name"] == "labels"
                ),
                Filter(
                    lambda payload:
                    payload["property_name"] == "labels" and "krules.dev/app" in payload["value"]
                ),
                SubjectNameMatch(
                    "^k8s:/apis/(?P<api_version>.+)/namespaces/(?P<namespace>.+)/(?P<resources>.+)/(?P<service_name>.+)$"
                ),
                Filter(
                    lambda payload:
                    payload["subject_match"]["api_version"] == "apps/v1"
                    and payload["subject_match"]["resources"] == "deployments"
                    or
                    payload["subject_match"]["api_version"] == "serving.knative.dev/v1"
                    and payload["subject_match"]["resources"] == "services"
                ),
            ],
            processing: [
                SetBuildSource(
                    target_property="build_source"
                )
            ]
        }
    },
    {
        rulename: "on-scfgp-update-set-subject",
        description: """
            Update the configuration property of related subject
        """,
        subscribe_to: [
            "dev.knative.apiserver.resource.update",
            "dev.knative.apiserver.resource.add",
        ],
        ruledata: {
            filters: [
                Filter(
                    lambda payload:
                    payload["kind"] == "ServiceConfigurationProvider"
                ),
                Filter(
                    lambda payload:
                    payload["metadata"].get("annotations", {}).get("krules.dev/subject") is not None
                )
            ],
            processing: [
                UpdateSubjectConfigurationProperty(
                    subject=lambda payload: payload["metadata"].get("annotations", {}).get("krules.dev/subject"),
                    configuration=lambda payload: payload
                )
            ],
        },
    },
    {
        rulename: "on-cfgp-update-services",
        description: """
            Changes to the configuration providers require the recalculation 
            of the build sources of the services possibly involved
        """,
        subscribe_to: [
            "dev.knative.apiserver.resource.update",
            "dev.knative.apiserver.resource.add",
            "dev.knative.apiserver.resource.delete",
        ],
        ruledata: {
            filters: [
                Filter(
                    lambda payload:
                    payload["kind"] == "ConfigurationProvider"
                ),
            ],
            processing: [
                UpdateServices(
                    configuration=lambda payload: payload,
                    service_target_property="build_source",
                )
            ],
        }
    },
    # CHECK PODS CONTAINERS STATUS
    {
        rulename: "on-pod-updates-store-in-subject",
        description: """
            Annotate on subject pods container statuses
        """,
        subscribe_to: [
            "dev.knative.apiserver.resource.update",
            "dev.knative.apiserver.resource.add",
        ],
        ruledata: {
            filters: [
                Filter(
                    lambda payload:
                    payload["kind"] == "Pod" and \
                    "krules.dev/app" in payload["metadata"].get("labels", {}) and \
                    "krules.dev/api" in payload["metadata"].get("labels", {})
                ),
            ],
            processing: [
                SubjectAnnotatePodInfo(
                    resource=lambda payload: payload,
                ),
            ]
        }
    },
    {
        rulename: "on-pod-delete-remove-from-subject",
        description: """
            Remove annotated pod from subject
        """,
        subscribe_to: [
            "dev.knative.apiserver.resource.delete",
        ],
        ruledata: {
            filters: [
                Filter(
                    lambda payload:
                    payload["kind"] == "Pod" and \
                    "krules.dev/app" in payload["metadata"].get("labels", {}) and \
                    "krules.dev/api" in payload["metadata"].get("labels", {})
                ),
            ],
            processing: [
                RemoveAnnotatedPodInfo(
                    resource=lambda payload: payload,
                ),
            ]
        }
    },
    # DISPOSE TASKS
    {
        rulename: "on-build-source-dispose-task",
        description: """
            When the build_source property is updated, its content is stored in a configmap 
            which will be mounted by the task that will build the image.
        """,
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("build_source"),
                SubjectNameMatch(
                    "^k8s:/apis/(?P<api_version>.+)/namespaces/(?P<namespace>.+)/(?P<resources>.+)/(?P<service_name>.+)$"
                ),
            ],
            processing: [
                CreateBuildSourceConfigMap(payload_dest="cm_info"),
                DeleteTaskRuns(
                    service_name=lambda payload: payload["subject_match"]["service_name"]
                ),
                CreateTaskRun(
                    config_name=lambda payload: payload["cm_info"]["cm_name"],
                    service_name=lambda payload: payload["subject_match"]["service_name"]
                ),
            ],
        }
    },
    # SUBSCRIBE TASKRUNS
    {
        rulename: "on-taskrun-update-set-target-subject",
        description: """
            Subscribe to 'build-and-push' taskruns updates and set significant properties on 
            the subject representing the resource to deploy
        """,
        subscribe_to: [
            "dev.knative.apiserver.resource.update",
            "dev.knative.apiserver.resource.add",
        ],
        ruledata: {
            filters: [
                Filter(
                    lambda payload:
                    payload["kind"] == "TaskRun" and payload.get("metadata", {})
                        .get("name", "").startswith("taskrun-build-and-push-")
                ),
            ],
            processing: [
                OnTaskRunUpdatesSetSubject(
                    lambda payload: payload
                )
            ]
        }
    },
    # DEPLOY SERVICES
    {
        rulename: "on-new-digest-patch-kservice-revision",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        description: """
            A new image digest has been pushed, deploy a new knative service revision
        """,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("digest"),
                SubjectNameMatch(
                    "^k8s:/apis/serving.knative.dev/v1/namespaces/(?P<namespace>.+)/(?P<resources>.+)/(?P<service_name>.+)$"
                ),
            ],
            processing: [
                PatchKServiceImage(
                    service_name=lambda payload: payload['subject_match']['service_name'],
                    image=lambda payload: payload["value"].strip(),
                )
            ]
        }
    },
    {
        rulename: "on-new-digest-patch-deployment",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        description: """
            A new image digest has been pushed, deploy a new service revision
        """,
        ruledata: {
            filters: [
                OnSubjectPropertyChanged("digest"),
                SubjectNameMatch(
                    "^k8s:/apis/apps/v1/namespaces/(?P<namespace>.+)/(?P<resources>.+)/(?P<service_name>.+)$"
                ),
            ],
            processing: [
                PatchDeploymentImage(
                    deployment_name=lambda payload: payload['subject_match']['service_name'],
                    image=lambda payload: payload["value"].strip(),
                )
            ]
        }
    },
    {
        rulename: "delete-taskrun-for-deleted-services",
        subscribe_to: "dev.knative.apiserver.resource.delete",
        description: """
            When a previously deployed service is deleted, its related taskruns are also removed
        """,
        ruledata: {
            filters: [
                IsDeployableTarget(
                    lambda payload: payload
                ),
            ],
            processing: [
                DeleteTaskRuns(
                    service_name=lambda payload: payload["metadata"]["name"]
                )
            ]
        }
    },
    {
        rulename: "dispatch-property-changes",
        subscribe_to: SUBJECT_PROPERTY_CHANGED,
        description: """
            send out property changes (clean payload)
        """,
        ruledata: {
            # filters: [
            #     Filter(
            #         lambda payload: payload["property_name"] not in ["build_source"]
            #     )
            # ],
            processing: [
                Route(
                    payload=lambda payload: {
                        "property_name": payload["property_name"],
                        "value": payload["value"],
                        "old_value": payload["old_value"],
                    },
                    dispatch_policy=DispatchPolicyConst.DIRECT
                )
            ],
        }
    },
]
