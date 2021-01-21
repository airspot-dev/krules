import pprint
import hashlib

from .restapiclient import *
from .pusherclient import *
from .scheduler import *
from .slack import *


def hashed(name, *args, length=10):
    hash = ""
    for arg in args:
        hash += pprint.pformat(arg)
    return "{}-{}".format(name, hashlib.md5(hash.encode("utf8")).hexdigest()[:length])


