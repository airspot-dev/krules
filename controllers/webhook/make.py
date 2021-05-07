#!/usr/bin/env python
import os
import shutil
from glob import glob
from importlib.machinery import SourceFileLoader

KRULES_ROOT_DIR = os.environ.get("KRULES_ROOT_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir, os.path.pardir))
KRULES_LIBS_DIR = os.path.join(KRULES_ROOT_DIR, "libs")

try:
    import local_utils
except ImportError:
    local_utils = SourceFileLoader("local_utils",
                                   os.path.join(KRULES_ROOT_DIR, "local_utils", "__init__.py")).load_module()

from sane import *
from sane import _Help as Help

DOCKER_CMD = os.environ.get("DOCKER_CMD", shutil.which("docker"))
KUBECTL_CMD = os.environ.get("KUBECTL_CMD", shutil.which("kubectl"))

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
APP_DIR = "app"

SERVICE_NAME = os.environ.get("WEBHOOK_SERVICE_NAME", "krules-webhook")
#DOCKER_REGISTRY = os.environ.get("DOCKER_REGISTRY")
#TARGET_IMAGE = f"{DOCKER_REGISTRY}/{SERVICE_NAME}"

RELEASE_VERSION = os.environ.get("RELEASE_VERSION")

DEBUG_PROCEVENTS_SINK = os.environ.get("DEBUG_PROCEVENTS_SINK")
NAMESPACE = os.environ.get("NAMESPACE", "krules-system-dev")


KRULES_DEP_LIBS = [
    "krules-core",
    "krules-dispatcher-cloudevents",
    "krules-env",
    "krules-flask-env",
    "krules-k8s-functions",
]

DEP_LIBS = [
    "gunicorn==20.0.4"
]

local_utils.make_render_resource_recipe(ROOT_DIR, "Dockerfile.j2", {
    "release_version": RELEASE_VERSION,
    "krules_dep_libs": KRULES_DEP_LIBS,
    "dep_libs": DEP_LIBS,
}, hooks=['prepare_build'])

local_utils.make_build_recipe(
    name="build",
    root_dir=ROOT_DIR,
    docker_cmd=DOCKER_CMD,
    target=SERVICE_NAME,
    extra_conditions=[
        lambda: local_utils.copy_dirs(
            dirs=[
                os.path.join(ROOT_DIR, os.path.pardir, "common")
            ],
            dst=os.path.join(ROOT_DIR, ".common")
        ),
        lambda: not RELEASE_VERSION and local_utils.copy_dirs(
            map(lambda x: os.path.join(KRULES_LIBS_DIR, x), KRULES_DEP_LIBS),
            dst=os.path.join(ROOT_DIR, ".krules-libs")
        ),
    ],
    success_file=".build.success",
    out_file=".build.out",
    hook_deps=["prepare_build"]
)


local_utils.make_push_recipe(
    name="push",
    root_dir=ROOT_DIR,
    docker_cmd=DOCKER_CMD,
    target=SERVICE_NAME,
    extra_conditions=[
        lambda: os.path.exists(os.path.join(ROOT_DIR, ".build.success")) and Help.file_condition(
            sources=[os.path.join(ROOT_DIR, ".build.success")],
            targets=[os.path.join(ROOT_DIR, ".digest")]
        )()
    ],
    digest_file=".digest",
    release_version=RELEASE_VERSION,
    recipe_deps=["build"],
)

with local_utils.pushd(ROOT_DIR):
    k8s_templates = (
        *glob(f'k8s/*.yaml.j2'),
    )
    digest = open(".digest", "r").read()

for template in k8s_templates:
        local_utils.make_render_resource_recipe(ROOT_DIR, template, {
            "namespace": NAMESPACE,
            "ns_injection_lbl": os.environ.get('NS_INJECTION_LBL'),
            "name": SERVICE_NAME,
            "digest": digest,
        }, hooks=['render_resource'], extra_conditions=[
            lambda: local_utils.check_envvar_exists('NAMESPACE'),
            lambda: local_utils.check_envvar_exists('NS_INJECTION_LBL')
        ])

@recipe(info="Push the last built docker image", conditions=[
        lambda: local_utils.check_envvar_exists('NAMESPACE'),
        lambda: local_utils.check_envvar_exists('NS_INJECTION_LBL'),
        lambda: local_utils.check_cmd(KUBECTL_CMD),
    ], recipe_deps="push"
)
def deploy():
    pass


local_utils.make_clean_recipe(
    root_dir=ROOT_DIR,
    globs=[
        ".common",
        "k8s/*.yaml",
        ".krules-libs",
        "Dockerfile",
        ".build*",
    ]
)


sane_run()
