import base64
import uuid

import jsonpath_rw_ext as jp
from flask import request, jsonify, g, json
from krules_core.providers import proc_events_rx_factory, subject_factory
from krules_core.route.router import DispatchPolicyConst
from krules_flask_env import KRulesApp

app = KRulesApp("webhook")


def _manage_rules_errors(event):
    if event.get("got_errors", False):
        app.logger.error("error processing {}".format(event["name"]),
                         extra={
                             "props": {"exc_info": "\n".join(jp.match1("$..[*].exc_info", event))}
                         })
        g.response["allowed"] = False

        g.response["status"] = {"code": 500, "message": "exception in rule {}".format(event["name"])}


proc_events_rx_factory.subscribe(
    on_next=_manage_rules_errors
)

def _get_subject_from_request(request):
    group = request["requestKind"]["group"]
    kind = request["requestKind"]["kind"]

    obj = request.get("object")
    if obj is None:
        # delete op
        obj = request.get("oldObject")
    name = request.get("name", obj["metadata"].get("name",
                               obj["metadata"].get("generateName", "_")))
    event_info = {
        "source": "krules-webhook"
    }
    prefix = kind.lower()
    if kind == "Service" and group == "serving.knative.dev":
        prefix = "kservice"

    return prefix, subject_factory(f"{prefix}:{name}", event_info=event_info)


@app.route("/validate", methods=['POST'])
def validating_webhook():
    payload = request.get_json()

    app.logger.debug("BeginRequest", extra={"props": {"payload": payload}})

    g.step = "VALIDATE"
    g.response = {
        "allowed": True,
        "uid": payload["request"]["uid"]
    }
    payload["response"] = g.response

    prefix, subject = _get_subject_from_request(payload["request"])
    event_type = f"validate-{prefix}-{payload['request']['operation'].lower()}"

    app.router.route(
        event_type, subject, payload,
        dispatch_policy=DispatchPolicyConst.NEVER
    )
    app.logger.debug("EventProcessed")

    app.logger.info("AdmissionReview",
                    extra={'props': {
                        'step': g.step,
                        'subject': subject.name,
                        'event_type': event_type,
                        'operation': payload["request"]["operation"],
                        'response': g.response
                    }})

    return jsonify({
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "response": g.response
    })


@app.route("/mutate", methods=['POST'])
def mutating_webhook():
    payload = request.get_json()

    app.logger.debug("BeginRequest", extra={"props": {"payload": payload}})

    g.step = "MUTATE"
    g.response = {
        "uid": payload["request"]["uid"],
        "allowed": True,
    }
    payload["response"] = g.response

    prefix, subject = _get_subject_from_request(payload["request"])
    event_type = f"mutate-{prefix}-{payload['request']['operation'].lower()}"
    app.router.route(
        event_type, subject, payload,
        dispatch_policy=DispatchPolicyConst.NEVER
    )
    app.logger.debug("EventProcessed")

    app.logger.info("AdmissionReview",
                    extra={'props': {
                        'step': g.step,
                        'subject': subject.name,
                        'event_type': event_type,
                        #'__callables': app.router._callables,
                        'operation': payload["request"]["operation"],
                        'response': g.response,
                        #'patch': "patch" in g.response and g.response["patch"] or None
                    }})
    if "patch" in g.response:
        g.response["patch"] = base64.b64encode(json.dumps(g.response["patch"]).encode("utf8")).decode("utf8")
    return jsonify({
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "response": g.response
    })


@app.route("/", methods=["GET"])
def main():
    return "Kicking", 200
