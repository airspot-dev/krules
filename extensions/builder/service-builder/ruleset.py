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

def _get_svc_url(obj: dict):
    if obj.get("apiVersion").startswith("serving.knative.dev/"):
        url: str = obj.get("status", {}).get("url")
        if url is not None and not url.endswith(".cluster.local"):
            return url
    return None


# def _get_svc_revision(obj: dict):
#     if obj.get("apiVersion").startswith("serving.knative.dev/"):
#         for revision in obj.get("status", {}).get("traffic", []):
#             if revision.get("latestRevision"):
#                 return revision.get("revisionName")
#     elif obj.get("kind") == "Deployment":
#         return obj.get("metadata", {}).get("name")
#
#     return "Unknown"


def _get_subject_name(obj: dict):
    return f"krules:builder:{obj.get('metadata').get('namespace')}:services:{obj.get('metadata').get('name')}"


def _get_resource_api(obj: dict):
    if obj.get("apiVersion").startswith("serving.knative.dev/"):
        return "knative"
    elif obj.get("kind") == "Deployment":
        return "base"

    assert False


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
                SetSubjectProperty(
                    subject=lambda payload: _get_subject_name(payload),
                    property_name="api",
                    value=lambda payload: _get_resource_api(payload),
                    use_cache=False,
                    muted=True
                ),
                SetSubjectProperties(
                    subject=lambda payload: _get_subject_name(payload),
                    props=lambda payload: yaml.load(
                        payload["metadata"].get("annotations", {}).setdefault("krules.dev/props", "{}"),
                        Loader=yaml.SafeLoader
                    ),
                    use_cache=False,
                    unmuted="*"
                ),
                SetSubjectProperty(
                    subject=lambda payload: _get_subject_name(payload),
                    property_name="applied",
                    value=lambda payload: yaml.load(
                        payload["metadata"].get("annotations", {}).get("config.krules.dev/applied", "{}"),
                        Loader=yaml.SafeLoader
                    ),
                    use_cache=False,
                ),
                SetSubjectProperty(
                    subject=lambda payload: _get_subject_name(payload),
                    property_name="labels",
                    value=lambda payload: payload.get("metadata", {}).get("labels", {}),
                    use_cache=False,
                ),
                SetSubjectProperty(
                    subject=lambda payload: _get_subject_name(payload),
                    property_name="ready",
                    value=lambda payload: _get_svc_ready_status(payload),
                    use_cache=False,
                ),
                SetSubjectProperty(
                    subject=lambda payload: _get_subject_name(payload),
                    property_name="url",
                    value=lambda payload: _get_svc_url(payload),
                    use_cache=False,
                ),
                SetRevision(
                    subject=lambda payload: _get_subject_name(payload),
                    resource=lambda payload: payload
                )
                # SetSubjectProperty(
                #     subject=lambda payload: _get_subject_name(payload),
                #     property_name="_generation",
                #     value=lambda payload: payload.get("metadata", {}).get("generation"),
                # ),
                # SetSubjectProperty(
                #     subject=lambda payload: _get_subject_name(payload),
                #     property_name="revision",
                #     value=lambda payload: _get_svc_revision(payload),
                #     use_cache=False,
                # )
            ],
        }
    },
    # {
    #     rulename: "on-generation-change-set-revision",
    #     description: """
    #       Update revision on resource generation change accordignly to resource type.
    #       Uses knative revision or subject annotated replicaset name for deployments.
    #     """,
    #     subscribe_to: SUBJECT_PROPERTY_CHANGED,
    #     ruledata: {
    #         filters: [
    #             OnSubjectPropertyChanged("_generation")
    #         ],
    #         processing: [
    #             SetRevision(generation=lambda payload: str(payload["value"]))
    #         ]
    #     }
    # },
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
                    lambda payload:
                    subject_factory(
                        f"krules:builder:{payload['metadata']['namespace']}:services:{payload['metadata']['name']}"
                    ).flush()
                )
            ],
        }
    },
    {
        rulename: "on-replicaset-update-on-base-annotate-revision-no",
        description: """
          The deployment revision number is annotated on the subject in order to use the replicaset name as
          as service revision
        """,
        subscribe_to: [
            "dev.knative.apiserver.resource.update",
            "dev.knative.apiserver.resource.add",
            #"dev.knative.apiserver.resource.delete",
        ],
        ruledata: {
            filters: [
                Filter(
                    lambda payload:
                    payload["kind"] == "ReplicaSet"
                ),
                Filter(
                    lambda payload:
                    payload.get("metadata", {}).get("annotations", {}).get("krules.dev/api") == "base"
                    and "deployment.kubernetes.io/revision" in payload.get("metadata", {}).get("annotations", {})
                ),
            ],
            processing: [
                SubjectAnnotateReplicaSetRevisionNo()
            ]
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
                SubjectNameMatch(
                    "^krules:builder:(?P<namespace>.+):services:(?P<service_name>.+)$"
                ),
                # Filter(
                #     lambda subject: subject.name.startswith("k8s:")
                # ),
                Filter(
                    #lambda payload: payload["property_name"] in ["labels", "configuration"]
                    lambda payload: payload["property_name"] == "labels"
                ),
                Filter(
                    lambda payload:
                    payload["property_name"] == "labels" and "krules.dev/app" in payload["value"]
                ),
                # SubjectNameMatch(
                #     "^k8s:/apis/(?P<api_version>.+)/namespaces/(?P<namespace>.+)/(?P<resources>.+)/(?P<service_name>.+)$"
                # ),
                # Filter(
                #     lambda payload:
                #     payload["subject_match"]["api_version"] == "apps/v1"
                #     and payload["subject_match"]["resources"] == "deployments"
                #     or
                #     payload["subject_match"]["api_version"] == "serving.knative.dev/v1"
                #     and payload["subject_match"]["resources"] == "services"
                # ),
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
                    "krules.dev/api" in payload["metadata"].get("annotations", {})
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
                    "krules.dev/api" in payload["metadata"].get("annotations", {})
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
                    "^krules:builder:(?P<namespace>.+):services:(?P<service_name>.+)$"
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
                    "^krules:builder:(?P<namespace>.+):services:(?P<service_name>.+)$"
                ),
                Filter(
                    lambda subject: "api" in subject and subject.get("api") == "knative"
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
                    "^krules:builder:(?P<namespace>.+):services:(?P<service_name>.+)$"
                ),
                Filter(
                    lambda subject: "api" in subject and subject.get("api") == "base"
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
