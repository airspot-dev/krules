
#_messages_rxsubjects = {}


class TopicsDefault:

    RESULTS = "RulesResults"
    #RESULTS_FULL = "RulesResultsFull"
    ERRORS = "RulesErrors"


class RuleConst(object):
    """
    Basic consts
    """

    PROCESS_ID = "process_id"
    ORIGIN_ID = "origin_id"
    RULENAME = "rulename" # TODO.. rule_name/rulename
    DESCRIPTION = "description"
    SUBSCRIBE_TO = "subscribe_to"
    RULEDATA = "ruledata"

    FILTERS = "filters"
    PROCESSING = "processing"
    FINALLY = "finally"

    MESSAGE = "message"
    SUBJECT = "subject"
    RULE_NAME = "rule_name"
    SECTION = "section"
    FUNC_NAME = "func_name"
    PAYLOAD = "payload"
    ARGS = "args"
    KWARGS = "kwargs"
    RETURNS = "returns"
    PROCESSED = "processed"
    EVENT_INFO = "event_info"

    GOT_ERRORS = "got_errors"
    EXCEPTION = "exception"
    EXC_INFO = "exc_info"
    #EXC_ORDER = "exc_order"


class ConfigKeyConst(object):

    MESSAGE_TOPICS_PREFIX = "MESSAGE_TOPICS_PREFIX"

