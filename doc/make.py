#!/usr/bin/env python
from glob import glob
import subprocess
import shutil
import os
from importlib.machinery import SourceFileLoader

KRULES_ROOT_DIR = os.environ.get("KRULES_ROOT_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir))

try:
    import local_utils
except ImportError:
    local_utils = SourceFileLoader("local_utils",
                                   os.path.join(KRULES_ROOT_DIR, "local_utils", "__init__.py")).load_module()

from sane import *
from sane import _Help as Help

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
SOURCE_DIR = os.path.join(ROOT_DIR, "source")
BUILD_DIR = os.path.join(ROOT_DIR, "build")
RELEASE_VERSION = os.environ.get("RELEASE_VERSION")

local_utils.make_render_resource_recipes(
    root_dir=ROOT_DIR,
    globs=[os.path.join("source", "conf.py.j2")],
    context_vars= {
        "doc_libs": [
            os.path.join(KRULES_ROOT_DIR, "libs", "krules-core"),
            os.path.join(KRULES_ROOT_DIR, "libs", "krules-k8s-functions"),
        ],
        "release_version": RELEASE_VERSION
    },
    run_before=[
        lambda: local_utils.check_envvar_exists("RELEASE_VERSION")
    ],
    hooks=["source_config"]
)


@recipe(
    info="Build multiversion documentation",
    conditions=[
        Help.file_condition(
            sources=glob(os.path.join(SOURCE_DIR, "*")),
            targets=[BUILD_DIR]
        )
    ],
    hook_deps=["source_config"]
)
def html():
    Help.log("Building documentation..")
    if shutil.which("sphinx-multiversion"):
        subprocess.run(["sphinx-multiversion", SOURCE_DIR, os.path.join(BUILD_DIR, "html", "en")])
    else:
        Help.error("sphinx-multiversion not found! Pleas run \"pip install sphinx-multiversion\"")


local_utils.make_clean_recipe(
    root_dir=ROOT_DIR,
    globs=["build"]
)

sane_run(default=html)
