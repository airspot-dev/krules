#!/usr/bin/env python3
import os
import re

from krules_dev import sane_utils

from sane import *

sane_utils.load_env()

INSTALL_IPYTHON = int(os.environ.get("INSTALL_IPYTHON", "0"))

SUBJECTS_BACKENDS = "SUBJECTS_BACKENDS" in os.environ and \
                    re.split('; |, ', os.environ["SUBJECTS_BACKENDS"]) or []

SUPPORTS_POSTGRESQL = int(os.environ.get("SUPPORTS_POSTGRESQL", "0"))
SUPPORTS_MYSQL = int(os.environ.get("SUPPORTS_MYSQL", "0"))


sane_utils.make_render_resource_recipes(
    globs=[
        "*.j2",
    ],
    context_vars=lambda: {
        "image_base": sane_utils.get_image("ruleset-image-base"),
        "install_ipython": INSTALL_IPYTHON,
        "subjects_backends": SUBJECTS_BACKENDS,
        "supports_postgresql": SUPPORTS_POSTGRESQL,
        "supports_mysql": SUPPORTS_MYSQL,
    },
    hooks=[
        'prepare_build'
    ]
)

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


sane_utils.make_apply_recipe(
    name="apply",
    globs=[
        "k8s/*.yaml"
    ],
    hook_deps=[
        "prepare_resources"
    ],
)


sane_utils.make_build_recipe(
    name="build",
    hook_deps=[
        "prepare_build"
    ],
    run_before=[
        # KRules development environment only
        # (when RELEASE_VERSION is not set)
        lambda: [
            sane_utils.copy_source(
                src=f"subjects_storages/{backend}",
                dst=f".subjects-{backend}",
                condition=lambda: "RELEASE_VERSION" not in os.environ
            ) for backend in SUBJECTS_BACKENDS
        ],
    ]
)


sane_utils.make_push_recipe(
    name="push",
    recipe_deps=[
        "build"
    ],
)

sane_utils.make_clean_recipe(
    globs=[
        "Dockerfile",
        "env.py",
        "k8s/*.yaml",
        ".digest",
        ".subjects-*/"
    ],
)

sane_run("push")

