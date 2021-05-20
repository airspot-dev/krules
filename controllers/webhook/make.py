#!/usr/bin/env python
import os
import shutil

try:
    from krules_dev import sane_utils
except ImportError:
    print('\033[91mkrules local development support is not installed... run "pip install krules-dev-support"\033[0m')
    exit(-1)

from sane import *
from sane import _Help as Help


KRULES_ROOT_DIR = os.environ.get("KRULES_ROOT_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir, os.path.pardir))
KRULES_LIBS_DIR = os.path.join(KRULES_ROOT_DIR, "libs")

DOCKER_CMD = os.environ.get("DOCKER_CMD", shutil.which("docker"))
KUBECTL_CMD = os.environ.get("KUBECTL_CMD", shutil.which("kubectl"))

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
APP_DIR = "app"

SERVICE_NAME = os.environ.get("SERVICE_NAME", "krules-webhook")

RELEASE_VERSION = os.environ.get("RELEASE_VERSION")

DEBUG_PROCEVENTS_SINK = os.environ.get("DEBUG_PROCEVENTS_SINK")

NAMESPACE = os.environ.get("NAMESPACE", "krules-system-dev")
NS_INJECTION_LBL = os.environ.get("NS_INJECTION_LBL", "dev.krules.airspot.dev")

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

sane_utils.make_render_resource_recipes(ROOT_DIR, globs=["Dockerfile.j2"], context_vars={
    "release_version": RELEASE_VERSION,
    "krules_dep_libs": KRULES_DEP_LIBS,
    "dep_libs": DEP_LIBS,
}, hooks=['prepare_build'])

sane_utils.make_build_recipe(
    name="build",
    root_dir=ROOT_DIR,
    docker_cmd=DOCKER_CMD,
    target=SERVICE_NAME,
    run_before=[
        lambda: sane_utils.copy_dirs(
            dirs=[
                os.path.join(ROOT_DIR, os.path.pardir, "common")
            ],
            dst=os.path.join(ROOT_DIR, ".common")
        ),
        lambda: not RELEASE_VERSION and sane_utils.copy_dirs(
            map(lambda x: os.path.join(KRULES_LIBS_DIR, x), KRULES_DEP_LIBS),
            dst=os.path.join(ROOT_DIR, ".krules-libs")
        ),
    ],
    success_file=".build.success",
    out_file=".build.out",
    hook_deps=["prepare_build"]
)


sane_utils.make_push_recipe(
    name="push",
    root_dir=ROOT_DIR,
    docker_cmd=DOCKER_CMD,
    target=SERVICE_NAME,
    conditions=[
        Help.file_condition(
            sources=[os.path.join(ROOT_DIR, ".build.success")],
            targets=[os.path.join(ROOT_DIR, ".digest")]
        )
    ],
    digest_file=".digest",
    tag=RELEASE_VERSION,
    recipe_deps=["build"],
)


sane_utils.make_render_resource_recipes(
    ROOT_DIR,
    globs=[f'k8s/*.yaml.j2'],
    context_vars=lambda: {
        "namespace": NAMESPACE,
        "ns_injection_lbl": NS_INJECTION_LBL,
        "name": SERVICE_NAME,
        "digest": open(".digest", "r").read(),
        "debug_procevents_sink": DEBUG_PROCEVENTS_SINK,
    },
    hooks=['render_resource'],
    # run_before=[
    #     lambda: sane_utils.check_envvar_exists('NAMESPACE'),
    #     lambda: sane_utils.check_envvar_exists('NS_INJECTION_LBL')
    # ]
)


sane_utils.make_apply_recipe(
    name="apply",
    root_dir=ROOT_DIR,
    globs=["k8s/*.yaml"],
    kubectl_cmd=KUBECTL_CMD,
    # run_before=[
    #     lambda: sane_utils.check_envvar_exists('NAMESPACE'),
    #     lambda: sane_utils.check_envvar_exists('NS_INJECTION_LBL'),
    # ],
    recipe_deps=["push"],
    hook_deps=["render_resource"]
)


sane_utils.make_clean_recipe(
    root_dir=ROOT_DIR,
    globs=[
        ".common",
        "k8s/*.yaml",
        ".krules-libs",
        "Dockerfile",
        ".build*",
        ".digest"
    ]
)


sane_run('apply')
