#!/usr/bin/env python3
import os

from krules_dev import sane_utils

from sane import *

sane_utils.load_env()

APP_NAME = os.environ.get("IMAGE_NAME", "builder-apiserversource-subscriber")
IMAGE_NAME = os.environ.get("IMAGE_NAME", APP_NAME)
RELEASE_VERSION = os.environ.get("RELEASE_VERSION")

DEBUG_PROCEVENTS_SINK = os.environ.get("DEBUG_PROCEVENTS_SINK")

# making changes to these files will result in a new build
sane_utils.update_code_hash(
    globs=[
        "*.py",
    ],
    output_file=".code.digest"
)

# render the templates required by the build process
sane_utils.make_render_resource_recipes(
    globs=[
        "Dockerfile.j2",
    ],
    context_vars=lambda: {
        "image_base": sane_utils.get_image("ruleset-image-base"),
        "out_dir": ".build",
    },
    hooks=[
        'prepare_build'
    ],
)

# build ruleset image
sane_utils.make_build_recipe(
    name="build",
    hook_deps=[
        "prepare_build"
    ],
    code_digest_file=".code.digest",
    success_file=".build.success",
)

# push ruleset image then save his digest
sane_utils.make_push_recipe(
    name="push",
    recipe_deps=[
        "build"
    ],
    digest_file=".digest",
)

# render k8s resources templates
sane_utils.make_render_resource_recipes(
    globs=[
        "k8s/*.j2"
    ],
    out_dir="k8s",
    context_vars=lambda: {
        "app_name": sane_utils.check_env("APP_NAME"),
        "namespace": sane_utils.check_env("NAMESPACE"),
        "service_api": sane_utils.check_env("SERVICE_API"),
        "image": "RELEASE_VERSION" not in os.environ and
                  open(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".build/.digest"), "r").read()
                  or f"{os.environ['DOCKER_REGISTRY']}/{IMAGE_NAME}:{RELEASE_VERSION}",
        "debug_procevents_sink": DEBUG_PROCEVENTS_SINK,
    },
    hooks=[
        'prepare_deploy'
    ],
    recipe_deps=[
        'push'
    ]
)

# apply k8s resources
sane_utils.make_apply_recipe(
    name="apply",
    globs=[
        "k8s/*.yaml"
    ],
    hook_deps=[
        "prepare_deploy"
    ],
)

# clean
sane_utils.make_clean_recipe(
    name="clean",
    globs=[
        "k8s/*.yaml",
        ".build/"
    ],
)


@recipe(recipe_deps=["push", "apply"])
def all():
    pass


sane_run("all")
