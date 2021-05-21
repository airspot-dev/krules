#!/usr/bin/env python
import os
import shutil
import subprocess

try:
    from krules_dev import sane_utils
except ImportError:
    print('\033[91mkrules local development support is not installed... run "pip install krules-dev-support"\033[0m')
    exit(-1)

from sane import *
from sane import _Help as Help


KRULES_ROOT_DIR = os.environ.get("KRULES_ROOT_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir, os.path.pardir))
KRULES_LIBS_DIR = os.path.join(KRULES_ROOT_DIR, "libs")

DOCKER_CMD = os.environ.get("DOCKER_CMD", shutil.which("docker"))
KUBECTL_CMD = os.environ.get("KUBECTL_CMD", shutil.which("kubectl"))

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
APP_DIR = "app"

SERVICE_NAME = os.environ.get("SERVICE_NAME", "krules-helper")
DOCKER_REGISTRY = os.environ.get("DOCKER_REGISTRY")

RELEASE_VERSION = os.environ.get("RELEASE_VERSION")

RULESET_IMAGE_BASE = os.environ.get("RULESET_IMAGE_BASE")

DEBUG_PROCEVENTS_SINK = os.environ.get("DEBUG_PROCEVENTS_SINK")

NAMESPACE = os.environ.get("NAMESPACE", "krules-system-dev")

def _get_image_base():
    global RULESET_IMAGE_BASE, RELEASE_VERSION
    if RULESET_IMAGE_BASE is not None:
        return RULESET_IMAGE_BASE
    if RULESET_IMAGE_BASE is None and RELEASE_VERSION is not None:
        RULESET_IMAGE_BASE = f"krules-ruleset-image-base:{RELEASE_VERSION}"
    else:
        subprocess.run([os.path.join(KRULES_ROOT_DIR, "images", "ruleset-image-base", "make.py")])
        with open(os.path.join(KRULES_ROOT_DIR, "images", "ruleset-image-base", ".digest"), "r") as f:
            RULESET_IMAGE_BASE = f.read()
    return RULESET_IMAGE_BASE


sane_utils.make_render_resource_recipes(ROOT_DIR, globs=['Dockerfile.j2'], context_vars=lambda: {
    "ruleset_image_base": _get_image_base(),
}, hooks=['prepare_build'])

sane_utils.make_build_recipe(
    name="build",
    root_dir=ROOT_DIR,
    docker_cmd=DOCKER_CMD,
    target=SERVICE_NAME,
    run_before=[
        lambda: sane_utils.copy_dirs(
            dirs=[
                os.path.join(ROOT_DIR, os.path.pardir, "common", "cfgp")
            ],
            dst=os.path.join(ROOT_DIR, ".common")
        )
    ],
    success_file=".build.success",
    out_file=".build.out",
    hook_deps=["prepare_build"]
)


sane_utils.make_push_recipe(
    name="push",
    root_dir=ROOT_DIR,
    docker_cmd=DOCKER_CMD,
    target=SERVICE_NAME,
    conditions=[
        Help.file_condition(
            sources=[os.path.join(ROOT_DIR, ".build.success")],
            targets=[os.path.join(ROOT_DIR, ".digest")]
        )
    ],
    digest_file=".digest",
    tag=RELEASE_VERSION,
    recipe_deps=["build"],
)


sane_utils.make_render_resource_recipes(ROOT_DIR, globs=['k8s/*.yaml.j2'], context_vars=lambda: {
    "namespace": NAMESPACE,
    "name": SERVICE_NAME,
    "digest": open(".digest", "r").read(),
    "debug_procevents_sink": DEBUG_PROCEVENTS_SINK,
}, hooks=['render_resource'])


sane_utils.make_apply_recipe(
    name="apply",
    root_dir=ROOT_DIR,
    globs=["k8s/*.yaml"],
    kubectl_cmd=KUBECTL_CMD,
    recipe_deps=["push"],
    hook_deps=["render_resource"]
)


sane_utils.make_clean_recipe(
    root_dir=ROOT_DIR,
    globs=[
        ".common",
        "k8s/*.yaml",
        "Dockerfile",
        ".build*",
        ".digest"
    ]
)


sane_run('apply')
