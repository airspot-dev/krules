#!/usr/bin/env python
from importlib.machinery import SourceFileLoader
import os
from glob import glob

KRULES_ROOT_DIR = os.environ.get("KRULES_ROOT_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir))

try:
    import local_utils
except ImportError:
    local_utils = SourceFileLoader("local_utils", os.path.join(KRULES_ROOT_DIR, "local_utils", "__init__.py")).load_module()

from sane import *
from sane import _Help as Help

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))

K8S_RESOURCES_DIR = 'k8s'

with local_utils.pushd(ROOT_DIR):
    k8s_templates = (
        *glob(f'{K8S_RESOURCES_DIR}/*.yaml.j2'),
    )

NAMESPACE = os.environ.get("NAMESPACE", "krules-system-dev")
DOCKER_REGISTRY = os.environ.get("DOCKER_REGISTRY")


for template in k8s_templates:
        local_utils.make_render_resource_recipe(ROOT_DIR, template, {
            "namespace": NAMESPACE
        }, hooks=['render_resource'])


@recipe(info="Render k8s resources (yaml)", hook_deps=['render_resource'])
def yaml():
    pass


local_utils.make_clean_recipe(
    root_dir=ROOT_DIR,
    globs=[f"{K8S_RESOURCES_DIR}/*.yaml"]
)

sane_run(default=yaml, cli=True)

