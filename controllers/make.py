#!/usr/bin/env python
import shutil
from importlib.machinery import SourceFileLoader
import os
import subprocess

KRULES_ROOT_DIR = os.environ.get("KRULES_ROOT_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir))

try:
    import local_utils
except ImportError:
    local_utils = SourceFileLoader("local_utils",
                                   os.path.join(KRULES_ROOT_DIR, "local_utils", "__init__.py")).load_module()

from sane import *
from sane import _Help as Help

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))

K8S_RESOURCES_DIR = 'k8s'

NAMESPACE = os.environ.get("NAMESPACE", "krules-system-dev")
DOCKER_REGISTRY = os.environ.get("DOCKER_REGISTRY")

CONTROLLERS_HELPER_SERVICE_NAME = os.environ.get("CONTROLLERS_HELPER_SERVICE_NAME", "krules-helper")
CONTROLLERS_WEBHOOK_SERVICE_NAME = os.environ.get("CONTROLLERS_WEBHOOK_SERVICE_NAME", "krules-webhook")

local_utils.make_render_resource_recipes(ROOT_DIR, [f'{K8S_RESOURCES_DIR}/*.yaml.j2'], {
    "namespace": NAMESPACE
}, hooks=['render_resource'])


@recipe(info="Build and deploy the webhook controller", hook_deps=['render_resource'])
def webhook():
    Help.log("Applying webhook..")
    with local_utils.pushd(ROOT_DIR):
        subprocess.run(["./webhook/make.py", "apply"])


@recipe(info="Build and deploy the helper controller", hook_deps=['render_resource'])
def helper():
    Help.log("Applying helper..")
    with local_utils.pushd(ROOT_DIR):
        subprocess.run(["./helper/make.py", "apply"], env={"SERVICE_NAME": CONTROLLERS_HELPER_SERVICE_NAME})


@recipe(info="Build and deploy all controllers", recipe_deps=[webhook, helper])
def controllers():
    Help.log("Controllers applied successfully")


local_utils.make_clean_recipe(
    root_dir=ROOT_DIR,
    globs=[f"{K8S_RESOURCES_DIR}/*.yaml"],
    on_completed=lambda: (
        subprocess.run(["./webhook/make.py", "clean"]),
        subprocess.run(["./helper/make.py", "clean"]),
    )
)

sane_run(default=controllers, cli=True)
