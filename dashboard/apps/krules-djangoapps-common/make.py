#!/usr/bin/env python3

import shutil
import subprocess

from dotenv import load_dotenv

try:
    from krules_dev import sane_utils
except ImportError:
    print('\033[91mcannot import sane_utils... run "pip install krules-dev-support"\033[0m')
    exit(-1)

from sane import *
#from sane import _Help as Help

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))

load_dotenv(
    os.path.join(ROOT_DIR, ".env")
)
load_dotenv(
    # local development (in .gitignore)
    os.path.join(ROOT_DIR, ".env.local")
)
load_dotenv(
    # override previously set (in .gitignore)
    os.path.join(ROOT_DIR, ".env.override"),
    override=True
)

RELEASE_VERSION = os.environ.get("RELEASE_VERSION")


sane_utils.make_render_resource_recipes(
    ROOT_DIR,
    globs=[
        "setup.py.j2",
    ],
    context_vars=lambda: {
        'release_version': RELEASE_VERSION,
    },
    # run_before=[
    #     lambda: sane_utils.check_envvar_exists("RELEASE_VERSION")
    # ],
    hooks=[''])


sane_utils.make_clean_recipe(
    root_dir=ROOT_DIR,
    globs=["setup.py"]
)

sane_run("setup.py")