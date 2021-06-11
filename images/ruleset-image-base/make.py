#!/usr/bin/env python
import os

try:
    from krules_dev import sane_utils
except ImportError:
    print('\033[91mkrules-dev is not installed... run "pip install krules-dev-support"\033[0m')
    exit(-1)

from sane import sane_run

sane_utils.load_env()


KRULES_ROOT_DIR = os.environ.get("KRULES_ROOT_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir, os.path.pardir))

KRULES_LIBS_DIR = os.path.join(KRULES_ROOT_DIR, "libs")

KRULES_DEP_LIBS = [
    "krules-core",
    "krules-dispatcher-cloudevents",
    "krules-env",
    "krules-flask-env",
    "krules-k8s-functions"
]

DEV_REQUIREMENTS = [
    "dependency-injector==4.32.2"
]

sane_utils.make_render_resource_recipes(
    globs=[
        "Dockerfile.j2"
    ],
    context_vars={
        "release_version": os.environ.get('RELEASE_VERSION'),
        "dev_requirements": DEV_REQUIREMENTS,
        "krules_libs": KRULES_DEP_LIBS,
    },
    hooks=['prepare_build']
)

sane_utils.make_build_recipe(
    name="build",
    hook_deps=["prepare_build"],
    run_before=[
        lambda: 'RELEASE_VERSION' not in os.environ and sane_utils.copy_dirs(
            map(lambda x: os.path.join(KRULES_LIBS_DIR, x), KRULES_DEP_LIBS),
            dst=".krules-libs"
        )
    ]
)


sane_utils.make_push_recipe(
    name="push",
    digest_file=".digest",
    recipe_deps=["build"],
)

sane_utils.make_clean_recipe(
    globs=[
        "Dockerfile",
        ".digest",
        ".krules-libs"
    ]
)

sane_run("push")
