#!/usr/bin/env python
from subprocess import run

try:
    from krules_dev import sane_utils
except ImportError:
    print('\033[91mkrules-dev is not installed... run "pip install krules-dev-support"\033[0m')
    exit(-1)

from sane import *

sane_utils.load_env()


KRULES_ROOT_DIR = os.environ.get("KRULES_ROOT_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir, os.path.pardir, os.path.pardir))

DJANGOAPPS_LIBS_DIR = os.path.join(KRULES_ROOT_DIR, "dashboard", "apps")

DJANGOAPPS_DEP_LIBS = [
    "krules-djangoapps-common",
    "krules-djangoapps-scheduler",
]


def get_image_base():
    return sane_utils.get_buildable_image(
        location=os.path.join(KRULES_ROOT_DIR, "images"),
        dir_name="ruleset-image-base",
        use_release_version=True,
        environ_override="SCHEDULER_IMAGE_BASE",
    )

sane_utils.make_render_resource_recipes(
    globs=[
        "*.j2",
    ],
    context_vars=lambda: {
        "image_base": get_image_base(),
        "site_name": sane_utils.check_envvar_exists("SITE_NAME"),
        "configuration_key": sane_utils.check_envvar_exists("CONFIGURATION_KEY"),
        "supports_postgres": bool(sane_utils.check_envvar_exists("DJANGO_BACKEND_POSTGRES")),
        "supports_mysql": bool(sane_utils.check_envvar_exists("DJANGO_BACKEND_MYSQL")),
        "supports_redis": bool(sane_utils.check_envvar_exists("SUPPORTS_REDIS")),
        "djangoapps_libs": DJANGOAPPS_DEP_LIBS
    },
    hooks=['prepare_build']
)


sane_utils.make_build_recipe(
    name="build",
    hook_deps=[
        "prepare_build"
    ],
    run_before=[
        lambda: 'RELEASE_VERSION' not in os.environ and sane_utils.copy_dirs(
            map(lambda x: os.path.join(DJANGOAPPS_LIBS_DIR, x), DJANGOAPPS_DEP_LIBS),
            dst=".djangoapps-libs",
            make_recipes=[
                "setup.py"
            ]
        ),
    ]
)


sane_utils.make_push_recipe(
    name="push",
    digest_file=".digest",
    recipe_deps=[
        "build"
    ],
)


sane_utils.make_render_resource_recipes(
    globs=[
        "k8s/*.j2"
    ],
    context_vars=lambda: {
        "app_name": sane_utils.check_envvar_exists("APP_NAME"),
        "namespace": sane_utils.check_envvar_exists("NAMESPACE"),
    },
    hooks=[
        'prepare_deploy'
    ]
)


sane_utils.make_apply_recipe(
    name="apply",
    globs=["k8s/*.yaml"],
    hook_deps=["prepare_deploy"],
)

sane_utils.make_service_recipe(
    image=lambda: open(".digest", "r").read().rstrip(),
    labels={
        "krules.airspot.dev/app": "{APP_NAME}",
        "krules.airspot.dev/type": "ruleset",
        "config.krules.airspot.dev/django-orm": "inject",
    },
    kn_extra=(
      "--scale", "1",
      "--wait-timeout", "10",
      "--cluster-local",
    ),
    info="deploy service",
    recipe_deps=["push", "apply"],
)



sane_utils.make_clean_recipe(
    globs=[
        "Dockerfile",
        "k8s/*.yaml",
        ".digest",
        ".build.success",
        ".djangoapps-libs",
    ],
)

sane_run("service")
