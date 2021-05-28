import contextlib
import shutil
from glob import glob
from subprocess import run
from sane import *
from sane import _Help as Help


def check_envvar_exists(name):
    if name not in os.environ:
        Help.error(f'Environment variable {name} does not exists')
    return os.environ[name]


def check_cmd(cmd):

    if shutil.which(cmd) is None:
        Help.error(f'Command {cmd} not found in PATH')


def make_render_resource_recipes(root_dir, globs, context_vars, hooks=("render_resource",), extra_conditions=(),
                                 run_before=()):

    def _context_vars():
        if callable(context_vars):
            return context_vars()
        return context_vars

    def _make_render_resource_recipe(j2_template):

        resource_file = j2_template.split(".j2")[0]
        resource_older_than_template = (
            Help.file_condition(
                sources=[os.path.join(root_dir, j2_template)],
                targets=[os.path.join(root_dir, resource_file)]
            )
        )

        @recipe(name=resource_file,
                conditions=[
                    *extra_conditions,
                    resource_older_than_template,
                ],
                hooks=hooks,
                info=f'Process \'{j2_template}\'')
        def render_resource():
            with pushd(root_dir):
                for func in run_before:
                    func()
                from jinja2 import Template
                Help.log(f"Rendering {resource_file}")
                tmpl = Template(open(j2_template).read(), trim_blocks=True, lstrip_blocks=True, ).render(
                    _context_vars()
                )
                open(resource_file, 'w').write(tmpl)

    with pushd(root_dir):

        k8s_templates = []

        for file in globs:
            k8s_templates.extend(glob(file))

        for template in k8s_templates:
            _make_render_resource_recipe(
                template
            )


def make_build_recipe(name, root_dir, docker_cmd, target, success_file, out_file, hook_deps, conditions=(),
                      run_before=()):
    @recipe(name=name, info=f"Build the docker image for target {target}", conditions=conditions, hook_deps=hook_deps)
    def build():
        check_envvar_exists('DOCKER_REGISTRY')
        check_cmd(docker_cmd)
        for func in run_before:
            func()

        target_image = f'{os.environ.get("DOCKER_REGISTRY")}/{target}'
        Help.log(f'Building {target_image} from Dockerfile')
        with pushd(root_dir):
            with open(out_file, "w") as out:
                build_response = run(
                    f'{docker_cmd} build -t {target_image} .', shell=True,
                    stdout=out, stderr=out
                )
                if build_response.returncode == 0:
                    with open(success_file, "w") as f:
                        f.write(target_image)
            if build_response.returncode != 0:
                if os.path.exists(success_file):
                    os.unlink(success_file)
                Help.error(open(out_file, "r").read())


def make_push_recipe(name, root_dir, docker_cmd, target, digest_file, tag, recipe_deps, conditions=(),
                     run_before=()):
    @recipe(name=name, info="Push the latest built docker image", conditions=conditions, recipe_deps=recipe_deps)
    def push():
        check_envvar_exists('DOCKER_REGISTRY')
        check_cmd(docker_cmd)

        for func in run_before:
            func()

        target_image = f'{os.environ.get("DOCKER_REGISTRY")}/{target}'
        if tag:
            _tag = f'{target_image}:{tag}'
        else:
            _tag = target_image

        Help.log(f'Pushing {_tag}')

        with pushd(root_dir):
            if tag:
                response = run(
                    f'{docker_cmd} tag {target_image} {_tag}',
                    shell=True, capture_output=True
                )
                if response.returncode != 0:
                    Help.error(response.stderr.decode("utf-8"))
            response = run(
                f'{docker_cmd} push {_tag}',
                shell=True, capture_output=True
            )
            if response.returncode != 0:
                Help.error(response.stderr.decode("utf-8"))
            response = run(
                f'{docker_cmd} inspect --format="{{{{index .RepoDigests 0}}}}" {_tag}',
                shell=True, capture_output=True
            )
            if response.returncode != 0:
                Help.log(_tag)
                Help.error(response.stderr.decode())
            Help.log(f"new digest: {response.stdout.decode().rstrip()}")
            with open(digest_file, "wb") as f:
                f.write(response.stdout)


def make_apply_recipe(name, root_dir, globs, kubectl_cmd, recipe_deps, hook_deps, extra_conditions=(), run_before=()):
    @recipe(
        name=name,
        info="Apply all",
        conditions=[
            *extra_conditions
        ],
        recipe_deps=recipe_deps,
        hook_deps=hook_deps
    )
    def apply():

        check_cmd(kubectl_cmd)
        for func in run_before:
            func()

        with pushd(root_dir):
            k8s_files = []
            for file in globs:
                k8s_files.extend(glob(file))
            for file in sorted(k8s_files):
                Help.log(f"Applying {file}..")
                response = run(
                    f'{kubectl_cmd} apply -f {file}',
                    shell=True, capture_output=True
                )
                if response.returncode != 0:
                    Help.error(response.stderr.decode("utf-8"))
                Help.log(response.stdout.decode("utf-8").rstrip())


def make_clean_recipe(root_dir, globs, on_completed=lambda: None):
    @recipe(info="Clean up project")
    def clean():
        with pushd(root_dir):
            files = [*glob("sane.py")]
            for file in globs:
                files.extend(glob(file))
            for f in files:
                Help.log(f"removing {f}")
                if os.path.isdir(f):
                    shutil.rmtree(f)
                else:
                    os.unlink(f)
            on_completed()


@contextlib.contextmanager
def pushd(new_dir):
    old_dir = os.getcwd()
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(old_dir)


def copy_dirs(dirs, dst):
    os.makedirs(dst,  exist_ok=True)
    for p in dirs:
        to_path = os.path.join(dst, os.path.basename(p))
        if os.path.exists(to_path):
            shutil.rmtree(to_path)
        shutil.copytree(p, to_path)
