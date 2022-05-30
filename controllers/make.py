#!/usr/bin/env python
import glob
import os
import subprocess
import sys

KRULES_REPO_DIR = os.environ.get("KRULES_REPO_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir))
sys.path.append(os.path.join(KRULES_REPO_DIR, "dev_support", "krules-dev-support"))

from krules_dev import sane_utils

from sane import *
from sane import _Help as Help

sane_utils.load_env()

if not "NAMESPACE" in os.environ:
    if "RELEASE_VERSION" in os.environ:
        os.environ["NAMESPACE"] = "krules-system"
    else:
        dev_target = os.environ.get("KRULES_DEV_TARGET", "dev")
        os.environ["NAMESPACE"] = f"krules-system-{dev_target}"

if "SVC_ACC_NAME" not in os.environ:
    if "RELEASE_VERSION" in os.environ:
        os.environ["SVC_ACC_NAME"] = "krules-system"
    else:
        dev_target = os.environ.get("KRULES_DEV_TARGET", "dev")
        os.environ["SVC_ACC_NAME"] = f"krules-system-{dev_target}"

sane_utils.make_render_resource_recipes(
    globs=[
        f'k8s/*.yaml.j2'
    ],
    context_vars=lambda: {
        "namespace": sane_utils.check_env("NAMESPACE"),
        "svc_acc_name": sane_utils.check_env("SVC_ACC_NAME")
    },
    out_dir="k8s",
    hooks=[
        'render_resource'
    ]
)

sane_utils.make_apply_recipe(
    name="apply",
    globs=[
        "k8s/*.yaml"
    ],
    hook_deps=[
        "render_resource"
    ]
)


@recipe(hook_deps=["render_resource"])
def render_resource():
    pass


@recipe(recipe_deps=["render_resource"])
def release():
    if not "RELEASE_VERSION" in os.environ:
        Help.error("missing RELEASE_VERSION environment variable")
    Help.log("Generating release.yaml")
    with sane_utils.pushd(os.path.dirname(os.path.realpath(__file__))):
        Help.log("..for common resources")
        resources = []
        for resource in sorted(glob.glob("k8s/*.yaml")):
            resources.append(open(resource, "r").read())
        Help.log("..for webhook")
        try:
            folders = [
                "webhook",
                "helper",
            ]
            for folder in folders:
                make_py = os.path.abspath(os.path.join(folder, "make.py"))
                out = subprocess.run(
                    (make_py, "clean"),
                    capture_output=True, check=True
                ).stdout
                [Help.log(f"> {l}") for l in out.decode().splitlines()]
                out = subprocess.run(
                    (make_py, "render_resource"),
                    capture_output=True, check=True, env=dict(os.environ)
                ).stdout
                [Help.log(f"> {l}") for l in out.decode().splitlines()]
                for resource in sorted(glob.glob(f"{folder}/k8s/*.yaml")):
                    resources.append(open(resource, "r").read())
            open("release.yaml", "w").write("\n".join(resources))
        except subprocess.CalledProcessError as ex:
            Help.error(ex.stderr.decode())


sane_utils.make_clean_recipe(
    globs=[
        "k8s/*.yaml",
    ],
)

sane_run("apply")
