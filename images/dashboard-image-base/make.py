#!/usr/bin/env python3

import os

from krules_dev import sane_utils

from sane import sane_run


sane_utils.load_env()


KRULES_ROOT_DIR = os.environ.get("KRULES_ROOT_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir, os.path.pardir))

sane_utils.make_render_resource_recipes(
    globs=[
        "*.j2",
    ],
    context_vars=lambda: {
        "image_base": sane_utils.get_buildable_image(
            location=KRULES_ROOT_DIR,
            dir_name="dashboard"
        ),
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

sane_utils.make_clean_recipe(
    globs=[
        "Dockerfile",
        ".build.success",
        ".digest",
    ]
)

sane_run("push")