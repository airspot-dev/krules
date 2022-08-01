#!/usr/bin/env python3

import os

from sane import sane_run

from krules_dev import sane_utils

sane_utils.load_env()


if "RELEASE_VERSION" in os.environ:
    os.environ["DOCKER_REGISTRY"] = os.environ.get("RELEASE_DOCKER_REGISTRY", "gcr.io/airspot")

sane_utils.make_render_resource_recipes(
    globs=[
        "Dockerfile.j2"
    ],
    hooks=['prepare_build']
)

sane_utils.make_build_recipe(
    name="build",
    hook_deps=["prepare_build"],
)

sane_utils.make_push_recipe(
    name="push",
    tag=os.environ.get("RELEASE_VERSION"),
    digest_file=".digest",
    recipe_deps=["build"],
)


sane_utils.make_clean_recipe(
    globs=[
        ".build/",
    ]
)

sane_run("push")
