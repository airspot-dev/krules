#!/usr/bin/env python3
import os

try:
    from krules_dev import sane_utils
except ImportError:
    print('\033[91mcannot import sane_utils... run "pip install krules-dev-support"\033[0m')
    exit(-1)

from sane import *

sane_utils.load_env()


sane_utils.make_render_resource_recipes(
    globs=[
        "setup.py.j2",
    ],
    context_vars=lambda: {
        'release_version': os.environ.get("RELEASE_VERSION"),
    },
)


sane_utils.make_clean_recipe(
    globs=[
        "setup.py",
        "*.egg-info",
    ]
)

sane_run("setup.py")