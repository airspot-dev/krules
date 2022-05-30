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

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
APP_DIR = "app"

SERVICE_NAME = os.environ.get("SERVICE_NAME", "webhook")
IMAGE_NAME = os.environ.get("IMAGE_NAME", SERVICE_NAME)
RELEASE_VERSION = os.environ.get("RELEASE_VERSION")

KRULES_DEP_LIBS = [
    "krules-k8s-functions",
]

if "RELEASE_VERSION" in os.environ:
    os.environ["DOCKER_REGISTRY"] = os.environ.get("RELEASE_DOCKER_REGISTRY", "gcr.io/airspot")
    if "NAMESPACE" not in os.environ:
        os.environ["NAMESPACE"] = "krules-system"
    os.environ.pop("DEBUG_PROCEVENTS_SINK", None)
else:
    if not "NAMESPACE" in os.environ:
        dev_target = os.environ.get("KRULES_DEV_TARGET", "dev")
        os.environ["NAMESPACE"] = f"krules-system-{dev_target}"

DEBUG_PROCEVENTS_SINK = os.environ.get("DEBUG_PROCEVENTS_SINK")

if "SVC_ACC_NAME" not in os.environ:
    if "RELEASE_VERSION" in os.environ:
        os.environ["SVC_ACC_NAME"] = "krules-system"
    else:
        dev_target = os.environ.get("KRULES_DEV_TARGET", "dev")
        os.environ["SVC_ACC_NAME"] = f"krules-system-{dev_target}"

def _get_image_base():
    return sane_utils.get_buildable_image(
        location=os.path.join(KRULES_REPO_DIR, "images"),
        dir_name="ruleset-image-base",
    )


def _prepare_commons():
    sane_utils.copy_resources(
        src=[
            os.path.join(ROOT_DIR, os.path.pardir, "common", "cfgp"),
            os.path.join(ROOT_DIR, os.path.pardir, "common", "features"),
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
        'Dockerfile.j2'
    ], 
    context_vars=lambda: {
        "image_base": _get_image_base(),
        "release_version": RELEASE_VERSION,
        "krules_dep_libs": KRULES_DEP_LIBS,

    }, 
    hooks=['prepare_build']
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
    digest_file=".digest",
    recipe_deps=["build"],
)


sane_utils.make_render_resource_recipes(
    globs=[
        'k8s/*.yaml.j2'
    ],
    out_dir="k8s",
    context_vars=lambda: {
        "namespace": sane_utils.check_env("NAMESPACE"),
        "name": sane_utils.check_env("SERVICE_NAME"),
        "svc_acc_name": sane_utils.check_env("SVC_ACC_NAME"),
        "image": "RELEASE_VERSION" not in os.environ and
                  open(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".build/.digest"), "r").read()
                  or f"{os.environ['DOCKER_REGISTRY']}/{IMAGE_NAME}:{RELEASE_VERSION}",
        "debug_procevents_sink": DEBUG_PROCEVENTS_SINK,
    },
    hooks=['render_resource']
)


@recipe(hook_deps=["render_resource"], recipe_deps=["push"])
def render_resource():
    pass


sane_utils.make_service_recipe(
    image=lambda: open(".digest", "r").read().rstrip(),
    labels={
        "krules.dev/app": "{APP_NAME}",
    },
    kn_extra=(
      "--scale", "1",
      "--wait-timeout", "20",
      #"--cluster-local",
    ),
    info="deploy service",
    recipe_deps=["push", "apply"],
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
        "k8s/*.yaml",
        ".build/"
    ]
)


sane_run('apply')
