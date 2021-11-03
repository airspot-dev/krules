#!/usr/bin/env python

import os

from krules_dev import sane_utils

from sane import sane_run


sane_utils.load_env()


KRULES_REPO_DIR = os.environ.get("KRULES_REPO_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir, os.path.pardir))

if "RELEASE_VERSION" in os.environ:
    os.environ["DOCKER_REGISTRY"] = os.environ.get("RELEASE_DOCKER_REGISTRY", "gcr.io/airspot")


image_base = sane_utils.get_buildable_image(
    location=os.path.join(KRULES_REPO_DIR, "images"),
    dir_name="generic-image-base",
    use_release_version=True,
    environ_override="IMAGE_BASE",
)


sane_utils.make_render_resource_recipes(
    globs=[
        "*.j2",
        "site/*.j2"
    ],
    context_vars=lambda: {
        "image_base": image_base,
        "site_name": sane_utils.check_env("SITE_NAME"),
        "configuration_key": sane_utils.check_env("CONFIGURATION_KEY"),
        "supports_postgres": bool(sane_utils.check_env("DJANGO_BACKEND_POSTGRES")),
        "supports_mysql": bool(sane_utils.check_env("DJANGO_BACKEND_MYSQL")),
        "supports_redis": bool(sane_utils.check_env("SUPPORTS_REDIS")),

    },
    hooks=['prepare_build']
)


sane_utils.make_build_recipe(
    target=sane_utils.check_env('IMAGE_NAME'),
    hook_deps=["prepare_build"],
)

sane_utils.make_push_recipe(
    target=sane_utils.check_env("IMAGE_NAME"),
    digest_file=".digest",
    tag=os.environ.get("RELEASE_VERSION"),
    recipe_deps=["build"]
)

sane_utils.make_clean_recipe(
    globs=[
        "Dockerfile",
        "site/*.py",
        ".build.*",
        ".digest"
    ]
)

sane_run("push")
