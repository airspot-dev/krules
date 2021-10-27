#!/usr/bin/env python3
import os
import subprocess
from glob import glob

from krules_dev import sane_utils

from sane import *
from sane import _Help as Help

sane_utils.load_env()

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))

sane_utils.make_render_resource_recipes(
    globs=[
        "setup.py.j2",
    ],
    context_vars=lambda: {
        'release_version': os.environ.get("RELEASE_VERSION"),
    },
    hooks=[
        "prepare_setup"
    ]
)


@recipe(info="Make develop installation", hook_deps=["prepare_setup"])
def develop():
    with sane_utils.pushd(ROOT_DIR):
        subprocess.run(["python3", "setup.py", "develop"])


@recipe(
    info="Publish package to pipy",
    hook_deps=["prepare_setup"],
    conditions=[
        Help.file_condition(
            sources=glob(os.path.join(ROOT_DIR, "krules_djangoapps_scheduler")),
            targets=[os.path.join(ROOT_DIR, "build")]
        )
    ],
)
def release():
    sane_utils.check_cmd("twine")
    with sane_utils.pushd(ROOT_DIR):
        subprocess.run(["python3", "setup.py", "sdist"])
        subprocess.run(["twine", "upload", "dist/*"])

sane_utils.make_clean_recipe(
    globs=[
        "setup.py",
        "*.egg-info",
        "dist",
    ]
)

sane_run("setup.py")