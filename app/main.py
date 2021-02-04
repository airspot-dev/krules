import json
import os
from datetime import datetime

from dependency_injector import providers
from flask import Response
from flask import request
from krules_core.providers import subject_factory

from krules_core.route.router import DispatchPolicyConst
import env as app_env
import io

from cloudevents.sdk.event import v1
from cloudevents.sdk import marshaller

from krules_env.flask import KRulesApp

app = KRulesApp("ruleset")
app_env.init()


@app.route('/', methods=['POST'], auto_store_subjects=True)
def main():
    start_time = datetime.now()
    try:
        dispatch_policy = os.environ.get("DISPATCH_POLICY", DispatchPolicyConst.NEVER)

        m = marshaller.NewDefaultHTTPMarshaller()
        event = m.FromRequest(v1.Event(), request.headers, io.BytesIO(request.data), lambda x: json.load(x))
        event_info = event.Properties()
        event_info.update(event_info.pop("extensions"))
        event_data = event_info.pop("data")

        app.logger.debug("RCVR: {}".format(event_data))
        event_type = event_info.get("type")
        subject = event_info.get("subject", "sys-0")
        # TODO: important!!
        # need to find a way to avoid a return of messages from the same service
        # (for example when resending it again after intercepted in the first time)
        # this workaround only works when in a knative service or at least when SOURCE environment
        # variable is set

        if event_info["source"] == os.environ.get("K_SERVICE", os.environ.get("SOURCE")):
            return Response(status=201)

        event_info["originid"] = event_info.get("originid", event_info.get("id"))

        app.logger.debug("subject: {}".format(subject))
        app.logger.debug("event_data: {}".format(event_data))

        subject = subject_factory(name=subject, event_info=event_info, event_data=event_data)

        event_data["_event_info"] = event_info  # TODO: KRUL-155

        try:
            app.router.route(
                event_type, subject, event_data,
                dispatch_policy=dispatch_policy
            )
        finally:
            pass

        exec_time = (datetime.now() - start_time).total_seconds()
        app.logger.info("Event",
                        extra={'props': {
                            'event_info': event_info,
                            'type': event_type,
                            'subject': subject.name,
                            'exec_time': exec_time,
                            # 'headers': list(headers.keys())
                        }})
        return Response(status=200)

    except Exception as ex:
        app.logger.error(ex, exc_info=True)
        return Response(status=201)
