
from .providers import settings_factory
from . import ConfigKeyConst


_settings = settings_factory()
#import pdb; pdb.set_trace()


def format_message_name(message):
    return "{}{}".format(_settings.get(ConfigKeyConst.MESSAGE_TOPICS_PREFIX, ""), message)


_m = format_message_name


SUBJECT_PROPERTY_CHANGED = _m("SubjectPropertyChanged")
SUBJECT_PROPERTY_DELETED = _m("SubjectPropertyDeleted")
