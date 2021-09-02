#!/usr/bin/env python3
import os
import re

from krules_dev import sane_utils

from sane import *

sane_utils.load_env()

RELEASE_VERSION = os.environ.get("RELEASE_VERSION")
SUBJECTS_BACKENDS = "SUBJECTS_BACKENDS" in os.environ and \
                    re.split('; |, ', os.environ["SUBJECTS_BACKENDS"]) or []
SUPPORTS_POSTGRESQL = int(os.environ.get("SUPPORTS_POSTGRESQL", "0"))
SUPPORTS_MYSQL = int(os.environ.get("SUPPORTS_MYSQL", "0"))


sane_utils.copy_resources(
    [os.path.join(os.environ["KRULES_PROJECT_DIR"], "base", "env.py")],
    dst=".",
    make_recipes_before=[
        "{src}",
    ],
)

# making changes to these files will result in a new build
sane_utils.update_code_hash(
    globs=[
        "*.py"
    ],
    output_file=".code.digest"
)

# render the templates required by the build process
sane_utils.make_render_resource_recipes(
    globs=[
        "Dockerfile.j2",
    ],
    context_vars=lambda: {
        "image_base": sane_utils.get_image("generic-image-base"),
        "subjects_backends": SUBJECTS_BACKENDS,
        "supports_postgresql": SUPPORTS_POSTGRESQL,
        "supports_mysql": SUPPORTS_MYSQL,
        "release_version": RELEASE_VERSION,
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
        "service_api": os.environ["SERVICE_API"],
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
        "krules.airspot.dev/type": "generic"
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
        "Dockerfile",
        "k8s/*.yaml",
        ".digest",
        ".code.digest",
        ".build.success"
    ],
)

sane_run("service")
