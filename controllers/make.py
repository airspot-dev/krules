#!/usr/bin/env python
import os
import subprocess

KRULES_ROOT_DIR = os.environ.get("KRULES_ROOT_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir))

try:
    from krules_dev import sane_utils
except ImportError:
    print('\033[91mkrules-dev is not installed... run "pip install krules-dev"\033[0m')
    exit(-1)

from sane import *
from sane import _Help as Help

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))

K8S_RESOURCES_DIR = 'k8s'

NAMESPACE = os.environ.get("NAMESPACE", "krules-system-dev")
DOCKER_REGISTRY = os.environ.get("DOCKER_REGISTRY")

CONTROLLERS_HELPER_SERVICE_NAME = os.environ.get("CONTROLLERS_HELPER_SERVICE_NAME", "krules-helper")
CONTROLLERS_WEBHOOK_SERVICE_NAME = os.environ.get("CONTROLLERS_WEBHOOK_SERVICE_NAME", "krules-webhook")

sane_utils.make_render_resource_recipes(ROOT_DIR, [f'{K8S_RESOURCES_DIR}/*.yaml.j2'], {
    "namespace": NAMESPACE
}, hooks=['render_resource'])


@recipe(info="Build and deploy the webhook controller", hook_deps=['render_resource'])
def webhook():
    Help.log("Applying webhook..")
    with sane_utils.pushd(ROOT_DIR):
        webhook_env = os.environ.update({"SERVICE_NAME": CONTROLLERS_WEBHOOK_SERVICE_NAME})
        subprocess.run(["./webhook/make.py", "apply"], env=webhook_env)


@recipe(info="Build and deploy the helper controller", hook_deps=['render_resource'])
def helper():
    Help.log("Applying helper..")
    with sane_utils.pushd(ROOT_DIR):
        helper_env = os.environ.update({"SERVICE_NAME": CONTROLLERS_HELPER_SERVICE_NAME})
        subprocess.run(["./helper/make.py", "apply"], env=helper_env)


@recipe(info="Build and deploy all controllers", recipe_deps=[webhook, helper])
def controllers():
    Help.log("Controllers applied successfully")


sane_utils.make_clean_recipe(
    root_dir=ROOT_DIR,
    globs=[f"{K8S_RESOURCES_DIR}/*.yaml"],
    on_completed=lambda: (
        subprocess.run(["./webhook/make.py", "clean"]),
        subprocess.run(["./helper/make.py", "clean"]),
    )
)

sane_run(default=controllers, cli=True)
