
class BaseDispatcher(object):

    def dispatch(self, message, subject, payload, **extra):
        from .router import logger
        logger.debug("dispatch: {} {} {} | extra: {}".format(message, subject, payload, extra))
