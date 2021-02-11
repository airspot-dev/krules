from flask import Flask, g
import os
import json_logging
import logging
import sys
import importlib
from krules_env import init
from dependency_injector import providers
from krules_core.providers import (
    subject_factory,
    event_router_factory
)
from krules_core.utils import load_rules_from_rulesdata


def g_wrap(current, *args, **kwargs):
    event_info = kwargs.pop("event_info", None)
    if not getattr(g, "subjects"):
        g.subjects = []
    if event_info is None and len(g.subjects) > 0:
        event_info = g.subjects[0].event_info()
    subject = current(*args, event_info=event_info, **kwargs)
    g.subjects.append(subject)
    return subject


class KRulesApp(Flask):
    def __init__(
            self,
            import_name,
            static_url_path=None,
            static_folder="static",
            static_host=None,
            host_matching=False,
            subdomain_matching=False,
            template_folder="templates",
            instance_path=None,
            instance_relative_config=False,
            root_path=None,
    ):
        super().__init__(
            import_name,
            static_url_path,
            static_folder,
            static_host,
            host_matching,
            subdomain_matching,
            template_folder,
            instance_path,
            instance_relative_config,
            root_path
        )

        json_logging.init_flask()
        json_logging.init_request_instrument(self)

        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(int(os.environ.get("LOGGING_LEVEL", logging.INFO)))
        self.logger.addHandler(logging.StreamHandler(sys.stdout))
        self.logger.propagate = False

        self.logger_core = logging.getLogger("__core__")
        self.logger_core.setLevel(int(os.environ.get("CORE_LOGGING_LEVEL", logging.ERROR)))
        self.logger_core.addHandler(logging.StreamHandler(sys.stdout))
        self.logger_core.propagate = False

        self.logger_router = logging.getLogger("__router__")
        self.logger_router.setLevel(int(os.environ.get("ROUTER_LOGGING_LEVEL", logging.ERROR)))
        self.logger_router.addHandler(logging.StreamHandler(sys.stdout))
        self.logger_router.propagate = False

        self.req_logger = logging.getLogger("flask-request-logger")
        self.req_logger.setLevel(logging.ERROR)
        self.req_logger.propagate = False

        init()

        try:
            import env
            env.init()
        except ImportError:
            self.logger.warning("No app env defined!")

        subject_factory.override(providers.Factory(lambda *args, **kw: g_wrap(subject_factory.cls, *args, **kw)))

        try:
            m_rules = importlib.import_module("ruleset")
            load_rules_from_rulesdata(m_rules.rulesdata)
        except ModuleNotFoundError:
            self.logger.warning("No rules defined!")
        except Exception as ex:
            self.logger.error(str(ex))

        self.router = event_router_factory()

    def _wrap_function(self, view_func):

        exec(
            """def wrapper(view_func):
                    def wrapped_%s():
                        g.subjects = []
                        resp = view_func()
                        for sub in g.subjects:
                            sub.store()
                        return resp
                    return  wrapped_%s""" % (view_func.__name__, view_func.__name__))

        return eval("wrapper(view_func)")

    def route(self, rule, **options):
        wrap_subjects = options.pop("auto_store_subjects", False)
        base_decorator = super().route(rule, **options)

        def decorator(f):
            if wrap_subjects:
                f = self._wrap_function(f)
            return base_decorator(f)

        return decorator
