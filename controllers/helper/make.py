#!/usr/bin/env python

try:
    from krules_dev import sane_utils
except ImportError:
    print('\033[91mkrules local development support is not installed... run "pip install krules-dev-support"\033[0m')
    exit(-1)

from sane import *

sane_utils.load_env()


KRULES_ROOT_DIR = os.environ.get("KRULES_ROOT_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir, os.path.pardir))
KRULES_LIBS_DIR = os.path.join(KRULES_ROOT_DIR, "libs")

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
APP_DIR = "app"

SERVICE_NAME = os.environ.get("SERVICE_NAME", "webhook")
IMAGE_NAME = os.environ.get("IMAGE_NAME", SERVICE_NAME)
RELEASE_VERSION = os.environ.get("RELEASE_VERSION")


if "RELEASE_VERSION" in os.environ:
    os.environ["DOCKER_REGISTRY"] = os.environ.get("RELEASE_DOCKER_REGISTRY", "gcr.io/airspot")
    if "NAMESPACE" not in os.environ:
        os.environ["NAMESPACE"] = "krules-system"
    os.environ.pop("DEBUG_PROCEVENTS_SINK", None)
else:
    if not "NAMESPACE" in os.environ:
        os.environ["NAMESPACE"] = "krules-system-dev"

DEBUG_PROCEVENTS_SINK = os.environ.get("DEBUG_PROCEVENTS_SINK")


def _get_image_base():
    return sane_utils.get_buildable_image(
        location=os.path.join(KRULES_ROOT_DIR, "images"),
        dir_name="ruleset-image-base",
    )


def _prepare_commons():
    sane_utils.copy_dirs(
        src=[os.path.join(ROOT_DIR, os.path.pardir, "common", "cfgp")],
        dst=".common"
    )


sane_utils.make_render_resource_recipes(
    globs=[
        'Dockerfile.j2'
    ], 
    context_vars=lambda: {
        "image_base": _get_image_base(),
    }, 
    hooks=['prepare_build']
)

sane_utils.make_build_recipe(
    name="build",
    target=IMAGE_NAME,
    run_before=[
        _prepare_commons
    ],
    hook_deps=["prepare_build"]
)


sane_utils.make_push_recipe(
    name="push",
    target=IMAGE_NAME,
    digest_file=".digest",
    recipe_deps=["build"],
)


sane_utils.make_render_resource_recipes(
    globs=[
        'k8s/*.yaml.j2'
    ], 
    context_vars=lambda: {
        "namespace": sane_utils.check_envvar_exists("NAMESPACE"),
        "name": sane_utils.check_envvar_exists("SERVICE_NAME"),
        "image": "RELEASE_VERSION" not in os.environ and
                  open(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".digest"), "r").read()
                  or f"{os.environ['DOCKER_REGISTRY']}/{IMAGE_NAME}:{RELEASE_VERSION}",
        "debug_procevents_sink": DEBUG_PROCEVENTS_SINK,
    },
    hooks=['render_resource']
)


@recipe(hook_deps=["render_resource"], recipe_deps=["push"])
def render_resource():
    pass


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

sane_utils.make_apply_recipe(
    name="apply",
    globs=[
        "k8s/*.yaml"
    ],
    recipe_deps=["push"],
    hook_deps=["render_resource"]
)


sane_utils.make_clean_recipe(
    globs=[
        ".common",
        "k8s/*.yaml",
        "Dockerfile",
        ".digest"
    ]
)


sane_run('apply')
