#!/usr/bin/env python3
import os
import re

from krules_dev import sane_utils

from sane import *


sane_utils.load_env()

RELEASE_VERSION = os.environ.get("RELEASE_VERSION")
INSTALL_IPYTHON = int(os.environ.get("INSTALL_IPYTHON", "0"))
SUBJECTS_BACKENDS = "SUBJECTS_BACKENDS" in os.environ and \
                    re.split('; |, ', os.environ["SUBJECTS_BACKENDS"]) or []

# making changes to these files will result in a new build
sane_utils.update_code_hash(
    globs=[
        "ipython_config.py",
    ],
    output_file=".code.digest"
)

# render the templates required by the build process
sane_utils.make_render_resource_recipes(
    globs=[
        "*.j2",
    ],
    context_vars=lambda: {
        "image_base": sane_utils.get_image("ruleset-image-base"),
        "install_ipython": INSTALL_IPYTHON,
        "subjects_backends": SUBJECTS_BACKENDS,
        "release_version": RELEASE_VERSION,
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
        "namespace": os.environ["NAMESPACE"],
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


# build image
sane_utils.make_build_recipe(
    name="build",
    hook_deps=[
        "prepare_build"
    ],
    run_before=[
        # KRules development environment only
        # (when RELEASE_VERSION is not set KRULES_ROOT_DIR must be set)
        lambda: [
            sane_utils.copy_source(
                src=f"subjects_storages/{backend}",
                dst=f".subjects-{backend}",
                condition=lambda: "RELEASE_VERSION" not in os.environ
            ) for backend in SUBJECTS_BACKENDS
        ],
    ],
    code_digest_file=".code.digest",
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
        "env.py",
        "k8s/*.yaml",
        ".digest",
        ".subjects-*/"
    ],
)

sane_run("push")

