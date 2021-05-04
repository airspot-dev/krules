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

NAMESPACE = os.environ.get("NAMESPACE", "krules-system-dev")
K8S_TEMPLATES_DIR = 'k8s'
K8S_RESOURCES_DIR = 'k8s'

k8s_templates = glob(f'{K8S_TEMPLATES_DIR}/*.yaml.j2')


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
        Help.log(f"Rendering {resource_file}")
        tmpl = Template(open(j2_template).read()).render(**vars)
        open(resource_file, 'w').write(tmpl)


@recipe(info="Clean up project")
def clean():
    Help.log("clean")
    files = [
            *glob("sane.py"),
            *glob("k8s/*.yaml")
        ]
    for f in files:
        os.unlink(f)

sane_run()
