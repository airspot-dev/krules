import logging
import os

import structlog
import sys
from sane import recipe as base_recipe

class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    default_format = "%(levelname)s - %(message)s"
    debug_format = "%(levelname)s - (%(pathname)s:%(filename)s:%(lineno)d) %(message)s"
    FORMATS = {
        logging.DEBUG: grey + debug_format + reset,
        logging.INFO: grey + default_format + reset,
        logging.WARNING: yellow + default_format + reset,
        logging.ERROR: red + default_format + reset,
        logging.CRITICAL: bold_red + default_format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
ch.setFormatter(CustomFormatter())

logger = logging.getLogger("__sane__")
logger.addHandler(ch)
logger.setLevel(logging.DEBUG)

# structlog.configure(
#     processors=[
#         structlog.contextvars.merge_contextvars,
#         structlog.processors.add_log_level,
#         structlog.processors.StackInfoRenderer(),
#         structlog.dev.set_exc_info,
#         structlog.processors.TimeStamper(),
#         structlog.dev.ConsoleRenderer()
#     ],
#     wrapper_class=structlog.make_filtering_bound_logger(logging.NOTSET),
#     context_class=dict,
#     logger_factory=structlog.PrintLoggerFactory(),
#     cache_logger_on_first_use=False
# )

# structlog.configure(
#     processors=[
#         structlog.stdlib.add_log_level,
#         structlog.stdlib.filter_by_level,
#         structlog.processors.TimeStamper(fmt='iso', utc=True),
#         structlog.processors.StackInfoRenderer(),
#         structlog.processors.format_exc_info,
#         structlog.processors.JSONRenderer()
#     ],
#     context_class=dict,
#     logger_factory=structlog.stdlib.LoggerFactory(),
#     wrapper_class=structlog.stdlib.BoundLogger,
#     cache_logger_on_first_use=True,
# )

log_level = int(os.environ.get("SANE_LOG_LEVEL", logging.INFO))
structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(log_level))


from .base import *

