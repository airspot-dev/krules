#!/usr/bin/env python
import os
import shutil

try:
    from krules_dev import sane_utils
except ImportError:
    print('\033[91mkrules-dev is not installed... run "pip install krules-dev"\033[0m')
    exit(-1)

from sane import *
from sane import _Help as Help

DOCKER_CMD = os.environ.get("DOCKER_CMD", shutil.which("docker"))

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
RELEASE_VERSION = os.environ.get("RELEASE_VERSION")
IMAGE_NAME = os.environ.get("IMAGE_NAME", "krules-generic-image-base")

KRULES_ROOT_DIR = os.environ.get("KRULES_ROOT_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir, os.path.pardir))
KRULES_LIBS_DIR = os.path.join(KRULES_ROOT_DIR, "libs")

KRULES_DEP_LIBS = ["krules-core", "krules-dispatcher-cloudevents", "krules-env"]
DEV_REQUIREMENTS = ["dependency-injector==4.32.2"]


sane_utils.make_render_resource_recipes(ROOT_DIR, globs=["Dockerfile.j2"], context_vars={
    "release_version": RELEASE_VERSION, "dev_requirements": DEV_REQUIREMENTS
}, hooks=['prepare_build'])


sane_utils.make_build_recipe(
    name="build",
    root_dir=ROOT_DIR,
    docker_cmd=DOCKER_CMD,
    target=IMAGE_NAME,
    success_file=".build.success",
    out_file=".build.out",
    hook_deps=["prepare_build"],
    run_before=[
        lambda: not RELEASE_VERSION and sane_utils.copy_dirs(
            map(lambda x: os.path.join(KRULES_LIBS_DIR, x), KRULES_DEP_LIBS),
            dst=os.path.join(ROOT_DIR, ".krules-libs")
        )
    ]
)


sane_utils.make_push_recipe(
    name="push",
    root_dir=ROOT_DIR,
    docker_cmd=DOCKER_CMD,
    target=IMAGE_NAME,
    conditions=[
        lambda: os.path.exists(os.path.join(ROOT_DIR, ".build.success")) and Help.file_condition(
            sources=[os.path.join(ROOT_DIR, ".build.success")],
            targets=[os.path.join(ROOT_DIR, ".digest")]
        )()
    ],
    digest_file=".digest",
    tag=RELEASE_VERSION,
    recipe_deps=["build"],
)

sane_utils.make_clean_recipe(
    root_dir=ROOT_DIR,
    globs=["Dockerfile", ".build.*", ".digest", ".krules-libs"]
)

sane_run("push")
