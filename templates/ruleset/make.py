#!/usr/bin/env python3
import os

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
        "image_base": sane_utils.get_image("ruleset-image-base"),
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
        "app_name": sane_utils.check_env("APP_NAME"),
        "namespace": sane_utils.check_env("NAMESPACE"),
        "service_api": sane_utils.check_env("SERVICE_API"),
    },
    hooks=[
        'prepare_deploy'
    ],
    recipe_deps=[
        'push'
    ]
)

sane_utils.make_subprocess_run_recipe(
    name="apply_base_resources",
    info="Apply resources from project's base",
    cmd=[
        os.path.join(os.environ["KRULES_PROJECT_DIR"], "base", "make.py"), "apply"
    ],
    hooks=[
        'prepare_deploy'
    ],
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
        "krules.airspot.dev/app": sane_utils.check_env("APP_NAME"),
        "krules.airspot.dev/type": "ruleset",
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
        ".build.success",
        ".user-baselibs",
    ],
)

sane_run("service")
