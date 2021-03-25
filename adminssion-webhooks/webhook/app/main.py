import base64

import jsonpath_rw_ext as jp
from flask import request, jsonify, g, json
from krules_core.providers import proc_events_rx_factory, subject_factory
from krules_core.route.router import DispatchPolicyConst
from krules_flask_env import KRulesApp

app = KRulesApp("webhook")

def _manage_procevents(event):
    app.logger.debug("processed {}".format(event["rule_name"]),
                     extra={
                         "props": {"event": event}
                     })
    if event.get("got_errors", False):
        app.logger.error("error processing {}".format(event["rule_name"]),
                         extra={
                             "props": {"exc_info": "\n".join(jp.match1("$..[*].exc_info", event))}
                         })
        g.response["allowed"] = False

        g.response["status"] = {"code": 500, "message": "exception in rule {}".format(event["rule_name"])}


proc_events_rx_factory.subscribe(
    on_next=_manage_procevents
)


@app.route("/validate", methods=['POST'])
def admission_webhook():
    payload = request.get_json()

    app.logger.debug("BeginRequest", extra={"props": {"payload": payload}})

    g.step = "VALIDATE"
    g.response = {
        "allowed": True,
        "uid": payload["request"]["uid"]
    }
    payload["response"] = g.response

    # subject = subject_factory("{}.{}.{}".format(
    #     payload["request"]["requestResource"]["resource"],
    #     payload["request"].get("name", payload["request"].get("object", {}).get("metadata", {}).get("name")),
    #     payload["request"].get("namespace", "_")
    # ))
    subject = subject_factory("__subject__")

    app.router.route(
        "validating-request", subject, payload,
        dispatch_policy=DispatchPolicyConst.NEVER
    )
    app.logger.debug("EventProcessed")

    app.logger.info("AdmissionReview",
                    extra={'props': {
                        'step': g.step,
                        'subject': subject.name,
                        'operation': payload["request"]["operation"],
                        'response': g.response
                    }})

    return jsonify({
        "apiVersion": "admission.k8s.io/v1beta1",
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

    # resource = payload["request"]["requestResource"]["resource"]
    # ob_name = payload["request"].get("object", {}).get("metadata", {}).get("generateName")
    # if ob_name is None:
    #     ob_name = payload["request"].get("object", {}).get("metadata", {}).get("name")
    # namespace = payload["request"].get("namespace", "_")
    #
    # subject = subject_factory("{}.{}.{}".format(resource, ob_name, namespace))
    subject = subject_factory("__subject__", event_info={"originid": "muatating"})
    app.router.route(
        "mutating-request", subject, payload,
        dispatch_policy=DispatchPolicyConst.NEVER
    )
    app.logger.debug("EventProcessed")

    app.logger.info("AdmissionReview",
                    extra={'props': {
                        'step': g.step,
                        'callables': len(app.router._callables),
                        'subject': subject.name,
                        'operation': payload["request"]["operation"],
                        'response': g.response,
                        'patch': "patch" in g.response and g.response["patch"] or None
                    }})
    if "patch" in g.response:
        g.response["patch"] = base64.b64encode(json.dumps(g.response["patch"]).encode("utf8")).decode("utf8")
    return jsonify({
        "apiVersion": "admission.k8s.io/v1beta1",
        "kind": "AdmissionReview",
        "response": g.response
    })


@app.route("/", methods=["GET"])
def main():
    return "Kicking", 200
