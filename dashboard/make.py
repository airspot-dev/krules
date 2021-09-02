#!/usr/bin/env python
import shutil


from krules_dev import sane_utils

from sane import sane_run, recipe, _Help as Help
import os

sane_utils.load_env()

KRULES_ROOT_DIR = os.environ.get("KRULES_ROOT_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir))
ENABLE_DJANGOAPP_PROCEVENTS = int(os.environ.get("ENABLE_DJANGOAPP_PROCEVENTS", "0"))
ENABLE_DJANGOAPP_SCHEDULER = int(os.environ.get("ENABLE_DJANGOAPP_SCHEDULER", "0"))

djangoapps_sources = [
    'krules-djangoapps-common',
]

if ENABLE_DJANGOAPP_PROCEVENTS:
    djangoapps_sources.append("krules-djangoapps-procevents")

if ENABLE_DJANGOAPP_SCHEDULER:
    djangoapps_sources.append("krules-djangoapps-scheduler")


# @recipe(info="Do whatever for each deployable django app", hooks=["prepare_build"])
# def djangoapps():
#
#     for app in djangoapps_sources:
#         try:
#             Help.log(f"Entering django app {app}")
#             run([
#                 os.path.join(os.path.dirname(os.path.realpath(__file__)), "apps", app, "make.py")
#             ], check=True)
#         except CalledProcessError:
#             Help.error(f"cannot make {app}")


image_base = lambda: sane_utils.get_buildable_image(
    location=os.path.join(KRULES_ROOT_DIR, "images"),
    dir_name="django-image-base",
    use_release_version=True,
    environ_override="IMAGE_BASE",
)


sane_utils.make_render_resource_recipes(
    globs=[
        "*.j2",
    ],
    context_vars=lambda: {
        "image_base": image_base(),
        "site_name": sane_utils.check_envvar_exists("SITE_NAME"),
        "app_name": sane_utils.check_envvar_exists("APP_NAME"),
        "configuration_key": sane_utils.check_envvar_exists("CONFIGURATION_KEY"),
        "djangoapps_sources": djangoapps_sources,
        "release_version":  os.environ.get("RELEASE_VERSION", False)
    },
    run_before=[
        lambda: 'RELEASE_VERSION' not in os.environ and sane_utils.copy_resources(
            map(lambda x: os.path.join("apps", x), djangoapps_sources),
            dst=".djangoapps-libs",
            make_recipes_after=[
                "setup.py"
            ]
        ),

    ],
    hooks=['prepare_build']
)

sane_utils.make_build_recipe(
    name="build",
    hook_deps=["prepare_build"],
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
        "configuration_key": sane_utils.check_envvar_exists("CONFIGURATION_KEY"),
        "djangoapps_sources": djangoapps_sources,
        "namespace": sane_utils.check_envvar_exists("NAMESPACE")
    },
    hooks=[
        'prepare_deploy'
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
    image=lambda: open(".digest", "r").read().rstrip(),
    labels={
        "krules.airspot.dev/app": "{APP_NAME}",
        "config.krules.airspot.dev/django-orm": "inject",
    },
    kn_extra=(
      "--scale", "1",
      "--wait-timeout", "20",
      #"--cluster-local",
    ),
    info="deploy service",
    recipe_deps=["push", "apply"],
)


sane_utils.make_clean_recipe(
    globs=[
        "Dockerfile",
        "k8s/*.yaml",
        ".digest",
        ".djangoapps-libs/"
    ],
    # on_completed=lambda: (
    #     run([os.path.join(os.path.dirname(os.path.realpath(__file__)), "apps", "krules-djangoapps-common", "make.py"), "clean"]),
    #     run([os.path.join(os.path.dirname(os.path.realpath(__file__)), "apps", "krules-djangoapps-procevents", "make.py"), "clean"]),
    #     run([os.path.join(os.path.dirname(os.path.realpath(__file__)), "apps", "krules-djangoapps-scheduler", "make.py"), "clean"]),
    # )
)

sane_run("service")
