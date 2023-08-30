#!/usr/bin/env python3
from subprocess import run

import krules_dev.sane_utils.deprecated
from krules_dev import sane_utils

from sane import *

sane_utils.load_env()


KRULES_DJANGO_APPS = [
    "krules-djangoapps-common",
    "krules-djangoapps-procevents",
]

sane_utils.update_code_hash(
    globs=[
        "*.py",
    ],
    output_file=".code.digest"
)

sane_utils.make_copy_source_recipe(
    name="prepare_djangoapps",
    location=os.path.join(os.environ.get("KRULES_REPO_DIR", ""), "django_apps"),
    src=KRULES_DJANGO_APPS,
    dst=".krules-djangoapps",
    make_recipes=("clean", "setup.py"),
    conditions=[
        lambda: "RELEASE_VERSION" not in os.environ and "KRULES_REPO_DIR" in os.environ
    ]
)

sane_utils.make_render_resource_recipes(
    globs=[
        "Dockerfile.j2",
    ],
    context_vars=lambda: {
        "image_base": sane_utils.get_image("ruleset-image-base"),
        "krules_djangoapps": KRULES_DJANGO_APPS,
        "use_postgresql": bool(sane_utils.check_env("DJANGO_BACKEND_POSTGRESQL")),
        "use_mysql": bool(sane_utils.check_env("DJANGO_BACKEND_MYSQL")),
    },
    hooks=[
        'prepare_build'
    ],
    recipe_deps=[
        "prepare_djangoapps"
    ]
)

sane_utils.make_build_recipe(
    name="build",
    hook_deps=[
        "prepare_build"
    ],
    build_args={
        "site_name": sane_utils.check_env("SITE_NAME"),
        "configuration_key": sane_utils.check_env("CONFIGURATION_KEY"),
    },
    code_digest_file=".code.digest",
    success_file=".build.success",
)

sane_utils.make_push_recipe(
    name="push",
    recipe_deps=[
        "build"
    ],
    digest_file=".digest",
)

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
        "prepare_deploy",
    ],
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

sane_utils.make_apply_recipe(
    name="apply",
    globs=[
        "k8s/*.yaml"
    ],
    hook_deps=[
        "prepare_deploy"
    ],
)

krules_dev.sane_utils.deprecated.make_service_recipe(
    name="service",
    labels={
        "krules.dev/app": sane_utils.check_env("APP_NAME"),
        "krules.dev/type": "ruleset",
        "config.krules.dev/django-orm": "inject",
    },
    env={},
    kn_extra=(
      "--scale", "1",
      "--wait-timeout", "10",
      "--cluster-local",
    ),
    recipe_deps=["push", "apply"],
)

sane_utils.make_clean_recipe(
    globs=[
        ".build/",
    ],
)

sane_run("service")
