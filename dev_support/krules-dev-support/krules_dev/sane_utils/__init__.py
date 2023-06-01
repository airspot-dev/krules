import logging
import sys

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
ch.setLevel(logging.INFO)
ch.setFormatter(CustomFormatter())

logger = logging.getLogger("__sane__")
logger.addHandler(ch)
logger.setLevel(logging.INFO)


from .base import *
