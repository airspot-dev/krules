from krules_core.base_functions import *

from krules_core import RuleConst as Const

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

from krules_core.providers import proc_events_rx_factory
from krules_env import publish_proc_events_errors, publish_proc_events_all, publish_proc_events_filtered

proc_events_rx_factory().subscribe(
    on_next=publish_proc_events_all,
)
# proc_events_rx_factory().subscribe(
#     on_next=publish_proc_events_errors,
# )


from django.apps import apps
from django.conf import settings
from django.db.utils import InterfaceError
apps.populate(settings.INSTALLED_APPS)
from configs.models import Configuration


Process = Returns

rulesdata = [

    """
    Store new Configuration resource in Django ORM
    """,
    {
        rulename: "on-configuration-creation-store-in-django",
        subscribe_to: "k8s.resource.add",
        ruledata: {
            filters: [
                Returns(
                    lambda _: (
                        "django.orm.configs/service" in _.payload["metadata"]["labels"] and
                        _.payload["kind"] == "Configuration"
                    )
                )
            ],
            processing: [
                Process(
                    lambda _: (
                        # current route set traffic => 0
                        Configuration.objects.filter(
                            service_id=int(_.payload["metadata"]["labels"]["django.orm.configs/service"])
                        ).update(traffic=0),
                        # new route get all traffic
                        Configuration.objects.create(
                            service_id=int(_.payload["metadata"]["labels"]["django.orm.configs/service"]),
                            name=_.payload["metadata"]["name"],
                            image=_.payload["spec"]["template"]["spec"]["containers"][0]["image"],
                            env=_.payload["spec"]["template"]["spec"]["containers"][0]["env"],
                            traffic=100
                        )
                    )
                )
            ],
        },
    },
    """
    Update Django model on Route update
    """,
    {
        rulename: "on-route-update-store-django-configs-traffic",
        subscribe_to: "k8s.resource.update",
        ruledata: {
            filters: [
                Returns(
                    lambda _: (
                        "django.orm.configs/service" in _.payload["metadata"]["labels"] and
                        _.payload["kind"] == "Route"
                    )
                )
            ],
            processing: [
                Process(
                    lambda _: (
                        [Configuration.objects.filter(name=config_traffic["configurationName"]).update(
                            traffic=int(config_traffic["percent"])
                        ) for config_traffic in _.payload["spec"]["traffic"]]
                    )
                ),
            ],
        },
    },

]