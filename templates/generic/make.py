#!/usr/bin/env python3
import os
import re

import krules_dev.sane_utils.deprecated
from krules_dev import sane_utils

from sane import *

sane_utils.load_env()

USER_BASELIBS = [
    # code you want to add to the container copied from base/libs directory
]

# making changes to these files will result in a new build
sane_utils.update_code_hash(
    globs=[
        "*.py",
        *list(map(lambda x: f"{os.environ['KRULES_PROJECT_DIR']}/base/{x}/**/*.py", USER_BASELIBS)),
    ],
    output_file=".code.digest"
)

# copy base libs
sane_utils.make_copy_source_recipe(
    name="prepare_user_baselibs",
    location=os.path.join(os.environ["KRULES_PROJECT_DIR"], "base", "libs"),
    src=USER_BASELIBS,
    dst=".user-baselibs",
)

# render the templates required by the build process
sane_utils.make_render_resource_recipes(
    globs=[
        "Dockerfile.j2",
    ],
    context_vars=lambda: {
        "image_base": sane_utils.get_image("generic-image-base"),
        "out_dir": ".build",
        "user_baselibs": USER_BASELIBS,
    },
    hooks=[
        'prepare_build'
    ],
    recipe_deps=[
        "prepare_user_baselibs",
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
        "service_api": os.environ["SERVICE_API"],
    },
    out_dir="k8s",
    hooks=[
        'prepare_deploy'
    ],
    recipe_deps=[
        'push'
    ]
)

krules_dev.sane_utils.deprecated.make_subprocess_run_recipe(
    name="apply_base_resources",
    info="Apply resources from project's base",
    cmd=[
        os.path.join(os.environ["KRULES_PROJECT_DIR"], "base", "make.py"), "apply"
    ],
    hooks=[
        "prepare_deploy"
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
krules_dev.sane_utils.deprecated.make_service_recipe(
    name="service",
    labels=lambda: {
        "krules.dev/app": os.environ["APP_NAME"],
        "krules.dev/type": "generic",
    },
    env={},
    # if SERVICE_API="knative" (requires kn client)
    kn_extra=(
      "--scale", "1",
      "--no-wait",
      #"--cluster-local",   # uncomment to make publically available
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
        #"k8s/*.yaml",
        ".build/"
    ],
)

sane_run("service")
