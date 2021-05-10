try:
    from sane import *
    from sane import _Help as Help
except ImportError:
    from urllib.request import urlretrieve

    urlretrieve("https://raw.githubusercontent.com/mikeevmm/sane/master/sane.py", "sane.py")
    from sane import *
    from sane import _Help as Help

    Help.warn('sane.py downloaded locally.. "pip install sane-build" to make it globally available')