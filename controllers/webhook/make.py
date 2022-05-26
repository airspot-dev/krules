#!/usr/bin/env python
import os
import sys

KRULES_REPO_DIR = os.environ.get("KRULES_REPO_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir, os.path.pardir ))
sys.path.append(os.path.join(KRULES_REPO_DIR, "dev_support", "krules-dev-support"))

from krules_dev import sane_utils

from sane import *

sane_utils.load_env()

KRULES_LIBS_DIR = os.path.join(KRULES_REPO_DIR, "libs")

APP_DIR = "app"

SERVICE_NAME = os.environ.get("SERVICE_NAME", "webhook")
IMAGE_NAME = os.environ.get("IMAGE_NAME", SERVICE_NAME)
RELEASE_VERSION = os.environ.get("RELEASE_VERSION")

DEBUG_PROCEVENTS_SINK = "RELEASE_VERSION" not in os.environ and os.environ.get("DEBUG_PROCEVENTS_SINK") or ""

KRULES_DEP_LIBS = [
    "krules-flask-env",
    "krules-k8s-functions",
]

KRULES_DEV_DEP_LIBS = [
    "krules-core",
    "krules-env",
    "krules-dispatcher-cloudevents"
]

DEP_LIBS = [
    "gunicorn==20.0.4"
]

if "RELEASE_VERSION" not in os.environ:
    KRULES_DEP_LIBS = KRULES_DEV_DEP_LIBS + KRULES_DEP_LIBS
    if "NAMESPACE" not in os.environ:
        dev_target = os.environ.get("KRULES_DEV_TARGET", "dev")
        os.environ["NAMESPACE"] = f"krules-system-{dev_target}"
else:
    os.environ["DOCKER_REGISTRY"] = os.environ.get("RELEASE_DOCKER_REGISTRY", "gcr.io/airspot")
    if "NAMESPACE" not in os.environ:
        os.environ["NAMESPACE"] = "krules-system"
    os.environ.pop("DEBUG_PROCEVENTS_SINK", None)

def _get_namespace():
    if not "NAMESPACE" in os.environ:
        if "RELEASE_VERSION" in os.environ:
            return "krules-system"
        else:
            dev_target = os.environ.get("KRULES_DEV_TARGET", "dev")
            return f"krules-system-{dev_target}"
    return os.environ["NAMESPACE"]


def _get_ns_injection_lbl():
    if not "NS_INJECTION_LBL" in os.environ:
        if "RELEASE_VERSION" in os.environ:
            return "krules.dev"
        else:
            dev_target = os.environ.get("KRULES_DEV_TARGET", "dev")
            return f"{dev_target}.krules.dev"
    return os.environ["NS_INJECTION_LBL"]




def _get_image_base():
    return sane_utils.get_buildable_image(
        location=os.path.join(KRULES_REPO_DIR, "images"),
        dir_name="generic-image-base",
    )


def _prepare_commons():
    sane_utils.copy_resources(
        src=[
            os.path.join(os.path.pardir, "common", "cfgp"),
            os.path.join(os.path.pardir, "common", "features"),
        ],
        dst=".build/.common"
    )


def _preprare_krules_deps():
    if not RELEASE_VERSION:
        sane_utils.copy_resources(
            map(lambda x: os.path.join(KRULES_LIBS_DIR, x), KRULES_DEP_LIBS),
            dst=".build/.krules-libs",
            make_recipes_after=[
                "clean", "setup.py"
            ]
        )


sane_utils.make_render_resource_recipes(
    globs=[
        "Dockerfile.j2"
    ],
    context_vars=lambda: {
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
    tag=os.environ.get("RELEASE_VERSION"),
    target=IMAGE_NAME,
    recipe_deps=["build"],
    digest_file=".digest"
)

sane_utils.make_render_resource_recipes(
    globs=[
        'k8s/*.yaml.j2'
    ],
    context_vars=lambda: {
        "namespace": sane_utils.check_env("NAMESPACE"),
        "ns_injection_lbl": _get_ns_injection_lbl(),
        "name": SERVICE_NAME,
        "image": "RELEASE_VERSION" not in os.environ and
                  open(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".build/.digest"), "r").read()
                  or f"{os.environ['DOCKER_REGISTRY']}/{IMAGE_NAME}:{RELEASE_VERSION}",
        "debug_procevents_sink": DEBUG_PROCEVENTS_SINK,
    },
    out_dir="k8s",
    hooks=['render_resource'],
)


@recipe(hook_deps=["render_resource"], recipe_deps=["push"])
def render_resource():
    pass


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
        "k8s/*.yaml",
        ".build/",
    ]
)

sane_run('apply')
