#!/usr/bin/env python

import shutil
import subprocess

from dotenv import load_dotenv

try:
    from krules_dev import sane_utils
except ImportError:
    print('\033[91mcannot import sane_utils... run "pip install krules-dev-support"\033[0m')
    exit(-1)

from sane import *
from sane import _Help as Help

load_dotenv()

DOCKER_CMD = os.environ.get("DOCKER_CMD", shutil.which("docker"))

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
RELEASE_VERSION = os.environ.get("RELEASE_VERSION")
IMAGE_NAME = os.environ.get("IMAGE_NAME", "krules-django-image-base")

KRULES_ROOT_DIR = os.environ.get("KRULES_ROOT_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir, os.path.pardir))
IMAGE_BASE = os.environ.get("IMAGE_BASE")

SITE_NAME = os.environ.get("SITE_NAME", "sitebase")
CONFIGURATION_KEY = os.environ.get("CONFIGURATION_KEY", "django")

DJANGO_BACKEND_POSTGRES = int(os.environ.get("DJANGO_BACKEND_POSTGRES", "0"))
DJANGO_BACKEND_MYSQL = int(os.environ.get("DJANGO_BACKEND_MYSQL", "0"))
SUPPORTS_REDIS = int(os.environ.get("SUPPORTS_REDIS", "0"))

def _get_image_base():
    global IMAGE_BASE, RELEASE_VERSION
    if IMAGE_BASE is not None:
        return IMAGE_BASE
    if IMAGE_BASE is None and RELEASE_VERSION is not None:
        IMAGE_BASE = f"krules-generic-image-base:{RELEASE_VERSION}"
    else:
        subprocess.run([os.path.join(KRULES_ROOT_DIR, "images", "generic-image-base", "make.py")])
        with open(os.path.join(KRULES_ROOT_DIR, "images", "generic-image-base", ".digest"), "r") as f:
            IMAGE_BASE = f.read()
    return IMAGE_BASE


sane_utils.make_render_resource_recipes(
    ROOT_DIR,
    globs=[
        "*.j2",
        "site/*.j2"
    ],
    context_vars=lambda: {
        "image_base": _get_image_base(),
        "site_name": SITE_NAME,
        "configuration_key": CONFIGURATION_KEY,
        "supports_postgres": bool(DJANGO_BACKEND_POSTGRES),
        "supports_mysql": bool(DJANGO_BACKEND_MYSQL),
        "supports_redis": bool(SUPPORTS_REDIS),

    },
    hooks=['prepare_build'])


sane_utils.make_build_recipe(
    name="build",
    root_dir=ROOT_DIR,
    docker_cmd=DOCKER_CMD,
    target=IMAGE_NAME,
    success_file=".build.success",
    out_file=".build.out",
    hook_deps=["prepare_build"],
    run_before=[
        # lambda: not RELEASE_VERSION and sane_utils.copy_dirs(
        #     map(lambda x: os.path.join(KRULES_LIBS_DIR, x), KRULES_DEP_LIBS),
        #     dst=os.path.join(ROOT_DIR, ".krules-libs")
        # )
    ]
)


sane_utils.make_push_recipe(
    name="push",
    root_dir=ROOT_DIR,
    docker_cmd=DOCKER_CMD,
    target=IMAGE_NAME,
    conditions=[
        lambda: os.path.exists(os.path.join(ROOT_DIR, ".build.success")) and Help.file_condition(
            sources=[os.path.join(ROOT_DIR, ".build.success")],
            targets=[os.path.join(ROOT_DIR, ".digest")]
        )()
    ],
    digest_file=".digest",
    tag=RELEASE_VERSION,
    # run_before=[
    #     lambda: sane_run("build")
    # ],
    recipe_deps=["build"]
)

sane_utils.make_clean_recipe(
    root_dir=ROOT_DIR,
    globs=["Dockerfile", "site/*.py", ".build.*", ".digest", ]
)

sane_run("push")
