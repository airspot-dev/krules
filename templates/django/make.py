#!/usr/bin/env python3

from krules_dev import sane_utils

from sane import *

sane_utils.load_env()

KRULES_DJANGO_APPS = [
    "krules-djangoapps-common",
    "krules-djangoapps-procevents",
    "krules-djangoapps-scheduler",
]

sane_utils.update_code_hash(
    globs=[
        "requirements.txt",
        "*.py",
    ],
    output_file=".code.digest"
)

sane_utils.make_copy_source_recipe(
    name="prepare_djangoapps",
    location="django_apps",
    src=KRULES_DJANGO_APPS,
    dst=".krules-djangoapps",
    conditions=[
        lambda: "RELEASE_VERSION" not in os.environ and "KRULES_ROOT_DIR" in os.environ
    ]
)


sane_utils.make_render_resource_recipes(
    globs=[
        "Dockerfile.j2",
    ],
    context_vars=lambda: {
        "image_base": sane_utils.get_image("generic-image-base"),
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
        "configuration_key": sane_utils.check_env("CONFIGURATION_KEY"),
    },
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
    labels=lambda: {
        "krules.airspot.dev/app": sane_utils.check_env("APP_NAME"),
        "krules.airspot.dev/type": "generic",
        "configs.krules.airspot.dev/django-orm": "inject",
    },
    env={},
    # if SERVICE_API="knative" (requires kn client)
    kn_extra=(
        "--scale", "1",
        "--no-wait",
        # "--cluster-local",   # uncomment to make publically available
    ),
    recipe_deps=[
        "push",
        "apply"
    ],
)

sane_utils.make_clean_recipe(
    name="clean",
    globs=[
        "Dockerfile",
        #"k8s/*.yaml",
        ".digest",
        ".code.digest",
        ".build.success",
        ".krules-djangoapps",
    ],
)

sane_run("service")
