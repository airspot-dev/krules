from krules_core.base_functions import *

from krules_core import RuleConst as Const
from krules_core.base_functions.misc import PyCall

rulename = Const.RULENAME
subscribe_to = Const.SUBSCRIBE_TO
ruledata = Const.RULEDATA
filters = Const.FILTERS
processing = Const.PROCESSING

from krules_core.providers import proc_events_rx_factory
from krules_env import publish_proc_events_errors, publish_proc_events_all, publish_proc_events_filtered, \
    RULE_PROC_EVENT

from krules_core.base_functions import RuleFunctionBase

from django.apps import apps
from django.conf import settings
from django.db.utils import InterfaceError
apps.populate(settings.INSTALLED_APPS)
from django_krules_procevents.models import ProcessedEvent
from datetime import datetime


# import pprint
# proc_events_rx_factory().subscribe(
#     on_next=lambda x: x["got_errors"] and pprint.pprint(x)
# )
# proc_events_rx_factory().subscribe(
#     on_next=publish_proc_events_all,
# )
# proc_events_rx_factory().subscribe(
#     on_next=publish_proc_events_errors,
# )

class DjangoStoreEvent(RuleFunctionBase):

    def execute(self):

        ProcessedEvent.objects.create(
            rule_name=self.payload["name"],
            type=self.payload["type"],
            subject=self.payload["subject"],
            event_info=self.payload["event_info"],
            payload=self.payload["payload"],
            time=self.payload["event_info"].get("time", datetime.now().isoformat()),
            filters=self.payload["filters"],
            processing=self.payload["processing"],
            got_errors=self.payload["got_errors"],
            processed=self.payload["processed"],
            origin_id=self.payload["event_info"].get("originid", "-")
        )

rulesdata = [

    """
    Store rules metrics in Django ORM
    """,
    {
        rulename: "django-orm-store-full-data",
        subscribe_to: RULE_PROC_EVENT,
        ruledata: {
            processing: [
                DjangoStoreEvent()
            ],
        },
    },

]