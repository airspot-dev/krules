#!/usr/bin/env python
import os
import re
import sys

KRULES_REPO_DIR = os.environ.get("KRULES_REPO_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir, os.path.pardir))
sys.path.append(os.path.join(KRULES_REPO_DIR, "dev_support", "krules-dev-support"))

from krules_dev import sane_utils

from sane import sane_run

sane_utils.load_env()

KRULES_LIBS_DIR = os.path.join(KRULES_REPO_DIR, "libs")

SUBJECTS_BACKENDS = "SUBJECTS_BACKENDS" in os.environ and \
                    re.split('; |, ', os.environ["SUBJECTS_BACKENDS"]) or []

SUBJECTS_BACKENDS_DIR = os.path.join(KRULES_REPO_DIR, "subjects_storages")

KRULES_DEP_LIBS = [
    "krules-core",
    "krules-dispatcher-cloudevents",
    "krules-env"
]

DEV_REQUIREMENTS = ["dependency-injector==4.39.1"]
GCP_SERVICE_ACCOUNT_PATH = None

if "RELEASE_VERSION" in os.environ:
    os.environ["DOCKER_REGISTRY"] = os.environ.get("RELEASE_DOCKER_REGISTRY", "gcr.io/airspot")

# if "GCP_SERVICE_ACCOUNT_PATH" in os.environ:
#     GCP_SERVICE_ACCOUNT_PATH = os.environ.get('GCP_SERVICE_ACCOUNT_PATH')
#     if GCP_SERVICE_ACCOUNT_PATH.endswith("/"):
#         GCP_SERVICE_ACCOUNT_PATH = GCP_SERVICE_ACCOUNT_PATH[:-1]
#     GCP_SERVICE_ACCOUNT_PATH = os.path.join(".build", os.path.split(GCP_SERVICE_ACCOUNT_PATH)[-1])


sane_utils.make_render_resource_recipes(
    globs=[
        "Dockerfile.j2"
    ],
    context_vars={
        "release_version": os.environ.get('RELEASE_VERSION'),
        "extra_index_url": os.environ.get('EXTRA_INDEX_URL'),
        "gcp_service_account_path": GCP_SERVICE_ACCOUNT_PATH,
        "dev_requirements": DEV_REQUIREMENTS,
        "subjects_backends":  SUBJECTS_BACKENDS
    },
    hooks=['prepare_build']
)


sane_utils.make_build_recipe(
    name="build",
    hook_deps=["prepare_build"],
    run_before=[
        lambda: 'RELEASE_VERSION' not in os.environ and sane_utils.copy_resources(
            map(lambda x: os.path.join(KRULES_LIBS_DIR, x), KRULES_DEP_LIBS),
            dst=".build/.krules-libs",
            make_recipes_hooks=[
                "clean", "setup.py"
            ]
        ),
        lambda: 'RELEASE_VERSION' not in os.environ and sane_utils.copy_resources(
            map(lambda x: os.path.join(SUBJECTS_BACKENDS_DIR, x), SUBJECTS_BACKENDS),
            dst=".build/.subjects-backends",
            make_recipes_hooks=[
                "clean", "setup.py"
            ]
        ),
        lambda: 'GCP_SERVICE_ACCOUNT_PATH' in os.environ and sane_utils.copy_resources(
            [os.environ.get('GCP_SERVICE_ACCOUNT_PATH'), ],
            dst="./.build",
            make_recipes_hooks=[
                "clean", "setup.py"
            ]
        )
    ]
)

sane_utils.make_push_recipe(
    name="push",
    tag=os.environ.get("RELEASE_VERSION"),
    digest_file=".digest",
    recipe_deps=["build"],
)

sane_utils.make_clean_recipe(
    globs=[
        ".build/",
    ]
)

sane_run("push")
