#!/usr/bin/env python3
from os import DirEntry

from krules_dev import sane_utils

from sane import *

sane_utils.load_env()

KRULES_DJANGOAPPS = [
    "krules-djangoapps-common",
    "krules-djangoapps-procevents",
    "krules-djangoapps-scheduler",
]

APPS_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "apps")

d: DirEntry
USER_DJANGOAPPS = [d.name for d in os.scandir(APPS_DIR) if d.is_dir() and d.name != '__pycache__']

sane_utils.update_code_hash(
    globs=[
        "requirements.txt",
        *list(map(lambda x: f"apps/{x}/**/*.py", USER_DJANGOAPPS)),
        "*.py",
    ],
    output_file=".code.digest"
)

sane_utils.make_copy_source_recipe(
    name="prepare_krules_djangoapps",
    location=os.path.join(os.environ.get("KRULES_REPO_DIR", ""), "django_apps"),
    src=KRULES_DJANGOAPPS,
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
        "image_base": sane_utils.get_image("generic-image-base"),
        "krules_djangoapps": KRULES_DJANGOAPPS,
        "user_djangoapps": USER_DJANGOAPPS,
        "use_postgresql": bool(sane_utils.check_env("DJANGO_BACKEND_POSTGRESQL")),
        "use_mysql": bool(sane_utils.check_env("DJANGO_BACKEND_MYSQL")),
        "out_dir": ".build",
    },
    hooks=[
        'prepare_build'
    ],
    recipe_deps=[
        "prepare_krules_djangoapps",
    ]
)

sane_utils.make_build_recipe(
    name="build",
    hook_deps=[
        "prepare_build",
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
    out_dir="k8s",
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
        "apply",
        "push",
    ],
)

sane_utils.make_clean_recipe(
    name="clean",
    globs=[
        ".build/",
    ],
)

sane_run("service")
