import yaml

from krules_core import RuleConst as Const
from krules_core.base_functions import *

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING


class AnnotateInProps(RuleFunctionBase):

    def execute(self, prop, value):
        """
        When the object is created the image is annotated as a base image.
        Any builds dependent on dynamic configurations will refer to this image
        """
        annotations = self.payload["__mutated_object"]["metadata"].setdefault("annotations", {})

        props = yaml.load(
            annotations.setdefault("krules.dev/props", "{}"),
            Loader=yaml.SafeLoader
        )

        props[prop] = value

        annotations["krules.dev/props"] = yaml.dump(props, Dumper=yaml.SafeDumper)


class Annotate(RuleFunctionBase):

    def execute(self, name: str, value):

        annotations = self.payload["__mutated_object"]["metadata"].setdefault("annotations", {})
        annotations[name] = value

        if "template" in self.payload["__mutated_object"].get("spec", {}):
            annotations = self.payload["__mutated_object"]["spec"]["template"]["metadata"].setdefault("annotations", {})
            annotations[name] = value




rulesdata = [
    """
    Initialize pods only when not owned by other objects
    """,
    {
        rulename: "initialize-pod",
        subscribe_to: [
            "mutate-pod-create",
        ],
        ruledata: {
            filters: [
                PayloadMatchOne(
                    "$.request.object.metadata.ownerReferences",
                    match_value=lambda v: v is None or len(v) == 0
                )
            ],
            processing: [
                AnnotateInProps(
                    lambda payload: payload["request"]["object"]["spec"]["containers"][0]["image"]
                ),
            ]
        }
    },
    """
    Initailize deployments only when not owned by other objects
    """,
    {
        rulename: "initialize-deployment",
        subscribe_to: [
            "mutate-deployment-create",
        ],
        ruledata: {
            filters: [
                PayloadMatchOne(
                    "$.request.object.metadata.ownerReferences",
                    match_value=lambda v: v is None or len(v) == 0
                )
            ],
            processing: [
                AnnotateInProps(
                    "image_base", lambda payload: payload["request"]["object"]["spec"]["template"]["spec"]["containers"][0]["image"]
                ),
                Annotate("krules.dev/api", "base"),
            ]
        }
    },
    """
    Initialize to knative services
    """,
    {
        rulename: "initialize-kservice",
        subscribe_to: [
            "mutate-kservice-create",
        ],
        ruledata: {
            processing: [
                AnnotateInProps(
                    lambda payload: payload["request"]["object"]["spec"]["template"]["spec"]["containers"][0]["image"]
                ),
                Annotate("krules.dev/api", "knative"),
            ]
        }
    },
]