#!/usr/bin/env python3


import os

try:
    from krules_dev import sane_utils
except ImportError:
    print('\033[91mcannot import sane_utils... run "pip install krules-dev-support"\033[0m')
    exit(-1)

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
        # "site_name": sane_utils.check_envvar_exists("SITE_NAME"),
        # "configuration_key": sane_utils.check_envvar_exists("CONFIGURATION_KEY"),
        # "supports_postgres": bool(sane_utils.check_envvar_exists("DJANGO_BACKEND_POSTGRES")),
        # "supports_mysql": bool(sane_utils.check_envvar_exists("DJANGO_BACKEND_MYSQL")),
        # "supports_redis": bool(sane_utils.check_envvar_exists("SUPPORTS_REDIS")),

    },
    hooks=['prepare_build']
)

sane_utils.make_build_recipe(
    name="build",
    hook_deps=["prepare_build"],
)


sane_utils.make_push_recipe(
    name="push",
    digest_file=".digest",
    recipe_deps=["build"],
)

sane_utils.make_clean_recipe(
    globs=[
        "Dockerfile",
        ".build.success",
        ".digest",
    ]
)

sane_run("push")