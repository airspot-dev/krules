#!/usr/bin/env python3
import os

from krules_dev import sane_utils

from sane import *


sane_utils.load_env()

# making changes to the files in this list will result in a new build
sane_utils.update_code_hash(
    globs=[
        "ruleset.py"
    ],
    output_file=".code.digest"
)

# render the templates required by the build process
sane_utils.make_render_resource_recipes(
    globs=[
        "Dockerfile.j2",
    ],
    context_vars=lambda: {
        "image_base": sane_utils.get_project_base("base"),
    },
    hooks=[
        'prepare_build'
    ]
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


# update or create service according to SERVICE_API environment variable (base/knative)
sane_utils.make_service_recipe(
    name="service",
    labels=lambda: {
        "krules.airspot.dev/app": os.environ["APP_NAME"],
        "krules.airspot.dev/type": "ruleset"
    },
    env={},
    # if SERVICE_API="knative" (requires kn client)
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


# clean
sane_utils.make_clean_recipe(
    name="clean",
    globs=[
        "Dockerfile",
        "k8s/*.yaml",
        ".digest",
        ".code.digest",
        ".build.success"
    ],
)

sane_run("service")
