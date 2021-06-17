#!/usr/bin/env python
import os
import shutil
import subprocess

try:
    from krules_dev import sane_utils
except ImportError:
    print('\033[91mkrules local development support is not installed... run "pip install krules-dev-support"\033[0m')
    exit(-1)


from sane import sane_run

sane_utils.load_env()

KRULES_ROOT_DIR = os.environ.get("KRULES_ROOT_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir, os.path.pardir))
KRULES_LIBS_DIR = os.path.join(KRULES_ROOT_DIR, "libs")

APP_DIR = "app"

SERVICE_NAME = os.environ.get("SERVICE_NAME", "webhook")
IMAGE_NAME = os.environ.get("IMAGE_NAME", SERVICE_NAME)
RELEASE_VERSION = os.environ.get("RELEASE_VERSION")

DEBUG_PROCEVENTS_SINK = os.environ.get("DEBUG_PROCEVENTS_SINK")

NAMESPACE = os.environ.get("NAMESPACE", "krules-system-dev")
NS_INJECTION_LBL = os.environ.get("NS_INJECTION_LBL", "dev.krules.airspot.dev")

KRULES_DEP_LIBS = [
    "krules-flask-env",
    "krules-k8s-functions",
]

DEP_LIBS = [
    "gunicorn==20.0.4"
]


def _get_image_base():
    return sane_utils.get_buildable_image(
        location=os.path.join(KRULES_ROOT_DIR, "images"),
        dir_name="generic-image-base",
    )


def _prepare_commons():
    sane_utils.copy_dirs(
        dirs=[os.path.join(os.path.pardir, "common", "cfgp")],
        dst=".common"
    )


def _preprare_krules_deps():
    if not RELEASE_VERSION:
        sane_utils.copy_dirs(
            map(lambda x: os.path.join(KRULES_LIBS_DIR, x), KRULES_DEP_LIBS),
            dst=".krules-libs",
        )


sane_utils.make_render_resource_recipes(
    globs=[
        "Dockerfile.j2"
    ],
    context_vars={
        "release_version": RELEASE_VERSION,
        "image_base": _get_image_base(),
        "krules_dep_libs": KRULES_DEP_LIBS,
        "dep_libs": DEP_LIBS,
    },
    hooks=[
        'prepare_build'
    ]
)


sane_utils.make_build_recipe(
    name="build",
    target=IMAGE_NAME,
    run_before=[
        _prepare_commons,
        _preprare_krules_deps,
    ],
    hook_deps=["prepare_build"]
)

sane_utils.make_push_recipe(
    name="push",
    target=IMAGE_NAME,
    recipe_deps=["build"],
    digest_file=".digest"
)

sane_utils.make_render_resource_recipes(
    globs=[
        'k8s/*.yaml.j2'
    ],
    context_vars=lambda: {
        "namespace": NAMESPACE,
        "ns_injection_lbl": NS_INJECTION_LBL,
        "name": SERVICE_NAME,
        "digest": open(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".digest"), "r").read(),
        "debug_procevents_sink": DEBUG_PROCEVENTS_SINK,
    },
    hooks=['render_resource'],
)

sane_utils.make_apply_recipe(
    name="apply",
    globs=[
        "k8s/*.yaml"
    ],
    recipe_deps=["push"],
    hook_deps=["render_resource"]
)

sane_utils.make_clean_recipe(
    globs=[
        ".common",
        "k8s/*.yaml",
        ".krules-libs",
        "Dockerfile",
        ".digest"
    ]
)

sane_run('apply')
