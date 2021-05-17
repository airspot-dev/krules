#!/usr/bin/env python
import subprocess
from glob import glob

from sane import *
from sane import _Help as Help

from krules_dev import sane_utils

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))

sane_utils.make_render_resource_recipes(
    root_dir=ROOT_DIR,
    globs=["setup.py.j2"],
    context_vars={
        "release_version": os.environ.get("RELEASE_VERSION"),
    },
    hooks=["prepare_setup"],
    run_before=[
        lambda: sane_utils.check_envvar_exists("RELEASE_VERSION")
    ],
)


@recipe(info="Make develop installation", hook_deps=["prepare_setup"])
def develop():
    with sane_utils.pushd(ROOT_DIR):
        subprocess.run(["python", "setup.py", "develop"])


@recipe(
    info="Publish package to pipy",
    hook_deps=["prepare_setup"],
    conditions=[
            Help.file_condition(
                sources=glob(os.path.join(ROOT_DIR, "krules_dev")),
                targets=[os.path.join(ROOT_DIR, "build")]
            )
    ],
)
def release():
    sane_utils.check_cmd("twine")
    with sane_utils.pushd(ROOT_DIR):
        subprocess.run(["python", "setup.py", "sdist"])
        subprocess.run(["twine", "upload", "dist/*"])


sane_utils.make_clean_recipe(
    root_dir=ROOT_DIR,
    globs=["setup.py", "dist", "*.eggs", "*.egg-info"]
)

sane_run()
