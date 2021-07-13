#!/usr/bin/env python3
import os

from krules_dev import sane_utils

from sane import *

sane_utils.load_env()


sane_utils.make_render_resource_recipes(
    globs=[
        "*.j2",
    ],
    context_vars=lambda: {
        "image_base": sane_utils.get_project_base("base"),
    },
    hooks=[
        'prepare_build'
    ]
)


sane_utils.make_build_recipe(
    name="build",
    hook_deps=[
        "prepare_build"
    ],
)


sane_utils.make_push_recipe(
    name="push",
    digest_file=".digest",
    recipe_deps=[
        "build"
    ],
)


sane_utils.make_render_resource_recipes(
    globs=[
        "k8s/*.j2"
    ],
    context_vars=lambda: {
        "app_name": os.environ["APP_NAME"],
        "namespace": os.environ["NAMESPACE"],
    },
    hooks=[
        'prepare_deploy'
    ],
    recipe_deps=[
        'push'
    ]

)


sane_utils.make_apply_recipe(
    name="apply",
    globs=[
        "k8s/*.yaml"
    ],
    hook_deps=[
        "prepare_deploy"
    ],
)


sane_utils.make_service_recipe(
    labels=lambda: {
        "krules.airspot.dev/app": os.environ["APP_NAME"],
    },
    env={},
    kn_extra=(
      "--scale", "1",
      "--no-wait",
      "--cluster-local",
    ),
    recipe_deps=[
        "push",
        "apply"
    ],
)


sane_utils.make_clean_recipe(
    globs=[
        "Dockerfile",
        "k8s/*.yaml",
        ".digest",
        ".build.success"
    ],
)

sane_run("service")
