#!/usr/bin/env python3
import os

from krules_dev import sane_utils

from sane import *


sane_utils.load_env()


# render the templates required by the build process
sane_utils.make_render_resource_recipes(
    globs=[
        "*.j2",
    ],
    context_vars=lambda: {
        "image_base": sane_utils.get_image("dashboard-image-base"),
        "site_name": sane_utils.check_env("SITE_NAME"),
        "configuration_key": sane_utils.check_env("CONFIGURATION_KEY"),
    },
    hooks=[
        'prepare_build'
    ]
)


# render k8s resources templates
sane_utils.make_render_resource_recipes(
    globs=[
        "k8s/*.j2",
    ],
    context_vars=lambda: {
        "namespace": sane_utils.check_env("NAMESPACE"),
    },
    hooks=[
        'prepare_resources'
    ]
)


# apply k8s resources
sane_utils.make_apply_recipe(
    name="apply",
    globs=[
        "k8s/*.yaml"
    ],
    hook_deps=[
        "prepare_resources"
    ],
)

sane_utils.make_service_recipe(
    image=lambda: open(".digest", "r").read().rstrip(),
    labels={
        "krules.airspot.dev/app": "{APP_NAME}",
        "krules.airspot.dev/type": "django-dashboard",
        "config.krules.airspot.dev/django-orm": "inject",
    },
    kn_extra=(
      "--scale", "1",
      "--wait-timeout", "20",
    ),
    info="deploy service",
    recipe_deps=[
        "push",
        "apply"
    ],
)


# build image
sane_utils.make_build_recipe(
    name="build",
    hook_deps=[
        "prepare_build"
    ],
)

# push image
sane_utils.make_push_recipe(
    name="push",
    recipe_deps=[
        "build"
    ],
)

# clean
sane_utils.make_clean_recipe(
    name="clean",
    globs=[
        "Dockerfile",
        "k8s/*.yaml",
        ".digest",
        "site/*.py",
    ],
)

sane_run("push")

