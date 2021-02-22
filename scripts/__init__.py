
deploy_py = """
name = "{name}"

add_files = (
    "ruleset.py",
)

add_modules = True  # find modules in directory (folders having __init__.py file) and add them to container

extra_commands = (
#    ("RUN", "pip install my-wonderful-lib==1.0"),
)

labels = {{
    "serving.knative.dev/visibility": "cluster-local",
    "krules.airspot.dev/type": "ruleset",
    "krules.airspot.dev/ruleset": name
}}

template_annotations = {{
    #"autoscaling.knative.dev/minScale": "0",
}}

#service_account = "my-service-account"

environ = {
    "PUBLISH_PROCEVENTS": "2",
    "PUBLISH_PROCEVENTS_FILTERS": "$[?(got_errors=true)]",
}

triggers = (
#    {{
#        "name": "test-trigger",
#        # broker: "my-broker",
#        "filter": {{
#            "attributes": {{
#                "type": "my-type"
#                # ...
#            }}
#        }}
#    }},
#    ...
)
triggers_default_broker = "default"

ksvc_sink = "broker:default"
ksvc_procevents_sink = "broker:procevents"

"""

dockerfile_skel = """\
FROM {image_base}

{add_section}

{extra_commands}
"""

ruleset_py = """
from krules_core.base_functions import *
from krules_core import RuleConst as Const

from krules_core.providers import proc_events_rx_factory
from krules_env import publish_proc_events_errors, publish_proc_events_all  #, publish_proc_events_filtered

try:
    from ruleset_functions import *
except ImportError:
    # for local development
    from .ruleset_functions import *


rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING


# proc_events_rx_factory.subscribe(
#   on_next=publish_proc_events_all,
# )
proc_events_rx_factory.subscribe(
 on_next=publish_proc_events_errors,
)

rulesdata = [
    \"""
    Rule description here..
    \""",
    {
        rulename: "rule-name",
        subscribe_to: ["event-type"],
        ruledata: {
            filters: [],
            processing: []
        }
    },
    # more rules here..
]

"""

ruleset_functions__init__py = """
from krules_core.base_functions import *

"""

README = """\
# {name}


"""