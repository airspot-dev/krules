#!/usr/bin/env python
import os
import sys
from glob import glob

try:
    from sane import *
    from sane import _Help as Help
except ImportError:
    from urllib.request import urlretrieve

    urlretrieve("https://raw.githubusercontent.com/mikeevmm/sane/master/sane.py", "sane.py")
    from sane import *
    from sane import _Help as Help

    Help.warn('sane.py downloaded locally.. "pip install sane-build" to make it globally available')

from sane import _Help as Help

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))

K8S_TEMPLATES_DIR = 'k8s'
K8S_RESOURCES_DIR = 'k8s'

k8s_templates = glob(f'{K8S_TEMPLATES_DIR}/*.yaml.j2')

NAMESPACE = os.environ.get("NAMESPACE", "krules-system-dev")
RELEASE_NAMESPACE = os.environ.get("NAMESPACE", "krules-system")
# RELEASE_VERSION = "0.9-pre1
DOCKER_REGISTRY = os.environ.get("DOCKER_REGISTRY")
RELEASE_DOCKER_REGISTRY = os.environ.get("RELEASE_DOCKER_REGISTRY")


def render_resource_recipe(j2_template, vars):
    basename = os.path.basename(j2_template).split(".j2")[0]
    resource_file = f'{K8S_RESOURCES_DIR}/{basename}'
    resource_older_than_template = (
        Help.file_condition(sources=[j2_template], targets=[resource_file])
    )


    @recipe(name=resource_file,
            conditions=[
                resource_older_than_template,
            ],
            hooks=['render_resource'],
            info=f'Render resource from template \'{j2_template}\'')
    def render_resource():
        check_jinja2()
        from jinja2 import Template
        Help.log(f"Rendering {resource_file}")
        tmpl = Template(open(j2_template).read()).render(**vars)
        open(resource_file, 'w').write(tmpl)


for template in k8s_templates:
    render_resource_recipe(template, {
        "namespace": NAMESPACE
    })


@recipe(info="Render k8s resources (yaml)", hook_deps=['render_resource'])
def yaml():
    pass


# def make_k8s_recipe(source_file):
#     @recipe(name=source_file,
#             conditions=[objects_older_than_source],
#             hooks=['compile'],
#             info=f'Compiles the file \'{source_file}\'')
#     def compile():
#         run(f'{CC} {COMPILE_FLAGS} -c {source_file} -o {obj_file}', shell=True)


# for source_file in k8s_templates:
#     make_k8s_recipe(source_file)

@recipe(info="Make and publish the release version")
def release():
    pass




# @recipe(info="Build the image")
# def image():
#     check_docker_registry()


# @recipe(info="Check jinja2 is installed")
def check_jinja2():
    try:
        import jinja2
    except ImportError:
        Help.error('Jinja2 is not installed... run "pip install jinja2"  (>=2.11.3)')
        exit(-1)


# @recipe(info="Check environment variables")
# def check_env():
#     if is_release:
#         pass
#     else:
#         pass
#     Help.log(f"NAMESPACE: {NAMESPACE}")

@recipe(info="Clean up project")
def clean():
    files = [
        *glob("sane.py"),
        *glob(f"{K8S_RESOURCES_DIR}/*.yaml")
    ]
    for f in files:
        Help.log(f"removing {f}")
        os.unlink(f)


sane_run()

# def check_docker_registry():
#     if DOCKER_REGISTRY is None:
#         Help.error('You must provide a DOCKER_REGISTRY environment variable')
#         exit(-1)
