#!/usr/bin/env python
import os

try:
    from krules_dev import sane_utils
except ImportError:
    print('\033[91mkrules-dev is not installed... run "pip install krules-dev"\033[0m')
    exit(-1)

from sane import sane_run

sane_utils.load_env()


KRULES_ROOT_DIR = os.environ.get("KRULES_ROOT_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir, os.path.pardir))
KRULES_LIBS_DIR = os.path.join(KRULES_ROOT_DIR, "libs")

KRULES_DEP_LIBS = [
    "krules-core",
    "krules-dispatcher-cloudevents",
    "krules-env"
]

DEV_REQUIREMENTS = ["dependency-injector==4.32.2"]

if "RELEASE_VERSION" in os.environ:
    os.environ["DOCKER_REGISTRY"] = os.environ.get("RELEASE_DOCKER_REGISTRY", "gcr.io/airspot")


sane_utils.make_render_resource_recipes(
    globs=[
        "Dockerfile.j2"
    ],
    context_vars={
        "release_version": os.environ.get('RELEASE_VERSION'),
        "dev_requirements": DEV_REQUIREMENTS
    },
    hooks=['prepare_build']
)


sane_utils.make_build_recipe(
    name="build",
    hook_deps=["prepare_build"],
    run_before=[
        lambda: 'RELEASE_VERSION' not in os.environ and sane_utils.copy_resources(
            map(lambda x: os.path.join(KRULES_LIBS_DIR, x), KRULES_DEP_LIBS),
            dst=".krules-libs",
            make_recipes_after=[
                "clean", "setup.py"
            ]
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
        ".krules-libs",
        ".build.success",
    ]
)

sane_run("push")
