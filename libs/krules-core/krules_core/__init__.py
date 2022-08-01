# Copyright 2019 The KRules Authors
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


class RuleConst(object):
    """
    Basic consts
    """

    PROCESS_ID = "process_id"
    ORIGIN_ID = "origin_id"
    RULENAME = "name"
    DESCRIPTION = "description"
    SUBSCRIBE_TO = "subscribe_to"
    RULEDATA = "data"

    FILTERS = "filters"
    PROCESSING = "processing"
    FINALLY = "finally"

    TYPE = "type"
    SUBJECT = "subject"
    SECTION = "section"
    FUNC_NAME = "function"
    PAYLOAD = "payload"
    ARGS = "args"
    KWARGS = "kwargs"
    RETURNS = "returns"
    PASSED = "passed"
    EVENT_INFO = "event_info"
    SOURCE = "source"

    GOT_ERRORS = "got_errors"
    EXCEPTION = "exception"
    EXC_INFO = "exc_info"
    EXC_EXTRA_INFO = "exc_extra_info"

    PAYLOAD_DIFFS = "payload_diffs"


# class ConfigKeyConst(object):
#
#     TYPE_TOPICS_PREFIX = "TYPE_TOPICS_PREFIX"


class ProcEventsLevel(object):

    DISABLED = 0
    LIGHT = 1
    FULL = 2
