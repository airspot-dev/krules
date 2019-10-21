from abc import ABCMeta, abstractmethod
#import jsonpath_rw_ext as jp
from krules_core.subject.tests.mocksubject import MockSubject


class with_payload(object):

    def __init__(self, func):
        self.func = func

    def __call__(self, payload):
        self._result = self.func(payload)
        return self._result

    def __repr__(self):
        if not hasattr(self, "_result"):
            return "[not called]"
        return str(self._result)

    def result(self):
        return getattr(self, "_result", None)

# TODO: with_payload_jp

# TODO: need testing
class with_subject(object):

    def __init__(self, func):
        self.func = func

    def __call__(self, subject):
        self._result = self.func(subject)
        return self._result

    def __repr__(self):
        if not hasattr(self, "_result"):
            return "[not called]"
        return str(self._result)

    def result(self):
        return getattr(self, "_result", None)

# TODO: with_subject_jp

# TODO: important! with_self

class RuleFunctionBase:

    __metaclass__ = ABCMeta

    # just for the ide happiness
    subject = MockSubject("mock")
    payload = {}
    message = ""

    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def _get_args(self, subject, payload):
        for _a in self._args:
            if isinstance(_a, with_payload):
                yield _a(payload)
            elif isinstance(_a, (list, tuple, dict)):
                yield self._parse_params(_a, payload)
            else:
                yield _a

    def _get_kwargs(self, subject, payload):
        _kwargs = self._kwargs.copy()
        return self._parse_params(_kwargs, payload)

    # TODO: with_subject, with_self
    def _parse_params(self, params, payload):
        for k in params:
            if isinstance(params, dict):
                index = k
            else:
                index = params.index(k)
            if isinstance(params[index], with_payload):
                params[index] = params[index](payload)
            elif isinstance(params[index], (list, tuple, dict)):
                params[index] = self._parse_params(params[index], payload)
        return params

    @abstractmethod
    def execute(self, *args, **kwargs):
        pass


from .filters import *
from .processing import *

