#!/usr/bin/env python
import glob
import os
import shutil
import subprocess

KRULES_ROOT_DIR = os.environ.get("KRULES_ROOT_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir))

try:
    from krules_dev import sane_utils
except ImportError:
    print('\033[91mkrules local development support is not installed... run "pip install krules-dev-support"\033[0m')
    exit(-1)

from sane import *
from sane import _Help as Help

sane_utils.load_env()


def _get_namespace():
    if not "NAMESPACE" in os.environ:
        if "RELEASE_VERSION" in os.environ:
            return "krules-system"
        else:
            return "krules-system-dev"
    return os.environ["NAMESPACE"]

#CONTROLLERS_HELPER_SERVICE_NAME = os.environ.get("CONTROLLERS_HELPER_SERVICE_NAME", "krules-helper")
#CONTROLLERS_WEBHOOK_SERVICE_NAME = os.environ.get("CONTROLLERS_WEBHOOK_SERVICE_NAME", "krules-webhook")

sane_utils.make_render_resource_recipes(
    globs=[
        f'k8s/*.yaml.j2'
    ],
    context_vars=lambda: {
        "namespace": _get_namespace()
    },
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
