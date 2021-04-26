from .. import RuleConst


def get_value_from_payload_diffs(key, payload_diffs, default_value=None):
    for patch in payload_diffs:
        if patch["path"] == "/%s" % key and patch["op"] in ("add", "replace"):
            return patch["value"]
    return default_value


def check_operation_on_property(property_name, payload, operation):
    for patch in payload[RuleConst.PAYLOAD_DIFFS]:
        if patch["path"] == "/%s" % property_name and patch["op"] == operation:
            return True
    return False
