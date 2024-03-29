#!/usr/bin/env python3
from subprocess import run

from krules_dev import sane_utils

from sane import *

sane_utils.load_env()


USER_DJANGOAPPS = [
    # your django applications in django/apps folder
]


sane_utils.update_code_hash(
    globs=[
        "*.py",
        *list(map(lambda x: f"{os.environ['KRULES_PROJECT_DIR']}/django/apps/{x}/**/*.py", USER_DJANGOAPPS)),
    ],
    output_file=".code.digest"
)

sane_utils.make_copy_source_recipe(
    name="prepare_user_djangoapps",
    location=os.path.join(os.environ["KRULES_PROJECT_DIR"], "django", "apps"),
    src=USER_DJANGOAPPS,
    dst=".user-djangoapps",
)

sane_utils.make_render_resource_recipes(
    globs=[
        "Dockerfile.j2",
    ],
    context_vars=lambda: {
        "image_base": sane_utils.get_image("ruleset-image-base"),
        "user_djangoapps": USER_DJANGOAPPS,
        "use_postgresql": bool(sane_utils.check_env("DJANGO_BACKEND_POSTGRESQL")),
        "use_mysql": bool(sane_utils.check_env("DJANGO_BACKEND_MYSQL")),
        "out_dir": ".build"
    },
    hooks=[
        'prepare_build'
    ],
    recipe_deps=[
        "prepare_user_djangoapps",
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
    out_dir="",
    hooks=[
        "prepare_deploy",
    ],
)

sane_utils.make_subprocess_run_recipe(
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

sane_utils.make_service_recipe(
    name="service",
    labels={
        "krules.airspot.dev/app": sane_utils.check_env("APP_NAME"),
        "krules.airspot.dev/type": "ruleset",
        "configs.krules.airspot.dev/django-orm": "inject",
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
        "Dockerfile",
#        "k8s/*.yaml",
        ".digest",
        ".code.digest",
        ".build.success",
        ".user-djangoapps",
    ],
)

sane_run("service")
