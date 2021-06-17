import contextlib
import inspect
import os
import shutil
import typing
from glob import glob
from subprocess import run, CalledProcessError

from dotenv import load_dotenv
from sane import *
from sane import _Help as Help


def check_envvar_exists(name):
    if name not in os.environ:
        Help.error(f'Environment variable {name} does not exists')
    return os.environ[name]


def check_cmd(cmd):
    cmd = shutil.which(cmd)
    if cmd is None:
        Help.error(f'Command {cmd} not found in PATH')
    return cmd


def load_env():
    abs_path = os.path.abspath(inspect.stack()[-1].filename)
    root_dir = os.path.dirname(abs_path)

    Help.log("Loading environment for {}".format(root_dir))
    load_dotenv(
        os.path.join(root_dir, ".env")
    )
    load_dotenv(
        # local development (in .gitignore)
        os.path.join(root_dir, ".env.local")
    )
    load_dotenv(
        # override previously set (in .gitignore)
        os.path.join(root_dir, ".env.override"),
        override=True
    )


def get_buildable_image(location: str,
                        dir_name: str,
                        name=None,
                        use_release_version=True,
                        environ_override: typing.Optional[str] = None,
                        push_cmd: str = "push",
                        digest_file: str = ".digest"):
    if environ_override is not None and environ_override in os.environ:
        return os.environ[environ_override]
    if use_release_version and 'RELEASE_VERSION' in os.environ:
        if name is None:
            name = f'krules-{dir_name}'
        return f'{name}:{os.environ["RELEASE_VERSION"]}'
    try:
        build_dir = os.path.join(location, dir_name)
        Help.log(f"Ensuring {digest_file} in {dir_name}")
        run([
            os.path.join(build_dir, "make.py"), push_cmd
        ], env={"PATH": os.environ["PATH"]}, capture_output=True, check=True)
        with open(os.path.join(build_dir, digest_file), "r") as f:
            return f.read().strip()
    except CalledProcessError as ex:
        Help.error(ex.stdout.decode())



def make_render_resource_recipes(globs: list,
                                 context_vars: typing.Union[dict, typing.Callable[[], dict]] = {},
                                 run_before: typing.Sequence[typing.Callable] = (),
                                 **recipe_kwargs):
    abs_path = os.path.abspath(inspect.stack()[-1].filename)
    root_dir = os.path.dirname(abs_path)

    def _context_vars():
        nonlocal context_vars
        if callable(context_vars):
            context_vars = context_vars()
        return context_vars



    def _make_render_resource_recipe(j2_template):

        resource_file = j2_template.split(".j2")[0]
        resource_older_than_template = (
            Help.file_condition(
                sources=[os.path.join(root_dir, j2_template)],
                targets=[os.path.join(root_dir, resource_file)]
            )
        )

        recipe_kwargs['info'] = "Render '{template}'".format(template=j2_template)
        if 'conditions' not in recipe_kwargs:
            recipe_kwargs['conditions'] = []
        recipe_kwargs['conditions'].append(resource_older_than_template)
        recipe_kwargs['name'] = resource_file

        @recipe(**recipe_kwargs)
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

        j2_templates = []

        for file in globs:
            j2_templates.extend(glob(file))

        for template in j2_templates:
            _make_render_resource_recipe(
                template
            )


def make_build_recipe(target: str = None,
                      run_before: typing.Sequence[typing.Callable] = (),
                      dockerfile: str = "Dockerfile",
                      **recipe_kwargs):
    abs_path = os.path.abspath(inspect.stack()[-1].filename)
    root_dir = os.path.dirname(abs_path)

    if target is None:
        target = check_envvar_exists('IMAGE_NAME')

    if 'name' not in recipe_kwargs:
        recipe_kwargs['name'] = 'build'
    docker_cmd = os.environ.get("DOCKER_CMD", check_cmd("docker"))
    success_file = f".{recipe_kwargs['name']}.success"
    if 'info' not in recipe_kwargs:
        recipe_kwargs['info'] = "Build the docker image for target {target}"
    recipe_kwargs['info'] = recipe_kwargs['info'].format(target=target)

    if 'conditions' not in recipe_kwargs:
        recipe_kwargs['conditions'] = []
    recipe_kwargs['conditions'].append(lambda: not os.path.exists(os.path.join(root_dir, success_file)))

    @recipe(**recipe_kwargs)
    def build():
        docker_registry = check_envvar_exists('DOCKER_REGISTRY')
        check_cmd(docker_cmd)
        target_image = f'{docker_registry}/{target}'
        Help.log(f'Building {target_image} from Dockerfile')

        for func in run_before:
            Help.log(f"..executing {func.__name__}")
            func()

        with pushd(root_dir):
            try:
                out = run(
                    f'{docker_cmd} build -t {target_image} -f {dockerfile} .', shell=True,
                    check=True, capture_output=True
                ).stdout
                [Help.log(f"> {l}") for l in out.decode().splitlines()]
                with open(success_file, "w") as f:
                    f.write(target_image)
            except CalledProcessError as ex:
                if os.path.exists(success_file):
                    os.unlink(success_file)
                Help.error(ex.stdout.decode())


def make_push_recipe(digest_file: str,
                     tag: str = os.environ.get("RELEASE_VERSION"),
                     target: str = None,
                     run_before: typing.Sequence[typing.Callable] = (),
                     dependent_build_recipe: str = "build",
                     **recipe_kwargs):
    abs_path = os.path.abspath(inspect.stack()[-1].filename)
    root_dir = os.path.dirname(abs_path)
    docker_cmd = os.environ.get("DOCKER_CMD", check_cmd("docker"))

    if 'name' not in recipe_kwargs:
        recipe_kwargs['name'] = "push"

    if target is None:
        target = os.environ.get('IMAGE_NAME')

    docker_registry = os.environ.get('DOCKER_REGISTRY')
    target_image = f"{docker_registry}/{target}"
    if tag:
        _tag = f'{target_image}:{tag}'
    else:
        _tag = target_image

    if 'info' not in recipe_kwargs:
        recipe_kwargs['info'] = f"Push image {_tag}"

    def _file_condition():
        try:
            _ret = Help.file_condition(
                sources=[os.path.join(root_dir, f".{dependent_build_recipe}.success")],
                targets=[os.path.join(root_dir, digest_file)]
            )()
        except TypeError:  # it happens when the success file is not found
            return False
        return _ret

    if 'conditions' not in recipe_kwargs:
        recipe_kwargs['conditions'] = []
    recipe_kwargs['conditions'].append(_file_condition)

    @recipe(**recipe_kwargs)
    def push():
        check_envvar_exists("IMAGE_NAME")
        check_envvar_exists("DOCKER_REGISTRY")

        for func in run_before:
            func()

        Help.log(f'Pushing {_tag}')

        with pushd(root_dir):
            try:
                if tag:
                    out = run(
                        f'{docker_cmd} tag {target_image} {_tag}',
                        shell=True, capture_output=True, check=True,
                    ).stdout
                    [Help.log(f"> {l}") for l in out.decode().splitlines()]
                out = run(
                    f'{docker_cmd} push {_tag}',
                    shell=True, capture_output=True, check=True,
                ).stdout
                [Help.log(f"> {l}") for l in out.decode().splitlines()]
                out = run(
                    f'{docker_cmd} inspect --format="{{{{index .RepoDigests 0}}}}" {_tag}',
                    shell=True, capture_output=True
                ).stdout
                with open(digest_file, "wb") as f:
                    f.write(out)
            except CalledProcessError as ex:
                Help.error(ex.stdout.decode())


def make_apply_recipe(globs: typing.Iterable[str], run_before: typing.Iterable[typing.Callable] = (), **recipe_kwargs):
    abs_path = os.path.abspath(inspect.stack()[-1].filename)
    root_dir = os.path.dirname(abs_path)

    if 'name' not in recipe_kwargs:
        recipe_kwargs['name'] = 'apply'
    if 'info' not in recipe_kwargs:
        recipe_kwargs['info'] = 'Apply k8s resources'

    @recipe(**recipe_kwargs)
    def apply():
        kubectl_cmd = os.environ.get("KUBECTL_CMD", check_cmd("kubectl"))
        check_cmd(kubectl_cmd)
        for func in run_before:
            func()

        with pushd(root_dir):
            k8s_files = []
            for file in globs:
                k8s_files.extend(glob(file))
            for file in sorted(k8s_files):
                Help.log(f"Applying {file}..")
                try:
                    out = run(
                        f'{kubectl_cmd} apply -f {file}',
                        shell=True, capture_output=True, check=True
                    ).stdout
                    [Help.log(f"> {l}") for l in out.decode().splitlines()]
                except CalledProcessError as ex:
                    Help.error(ex.stderr.decode())


def make_service_recipe(image: typing.Union[str, typing.Callable], labels: dict = {}, kn_extra: tuple = (),
                        env: typing.Union[dict, typing.Callable[[], dict]] = {},
                        **recipe_kwargs):
    abs_path = os.path.abspath(inspect.stack()[-1].filename)
    root_dir = os.path.dirname(abs_path)
    namespace = check_envvar_exists("NAMESPACE")
    service_api = os.environ.get("SERVICE_API", "base")
    service_type = os.environ.get("SERVICE_TYPE", "")
    kubectl_cmd = kubectl_opts = kn_cmd = kn_opts = None
    if service_api == "base":
        kubectl_cmd = os.environ.get("KUBECTL_CMD", check_cmd("kubectl"))
        kubectl_opts = os.environ.get("KUBECTL_OPTS", "").split()
    elif service_api == "knative":
        kn_cmd = os.environ.get("KN_CMD", check_cmd("kn"))
        kn_opts = os.environ.get("KN_OPTS", "").split()
    else:
        Help.error(f"unknown service api {service_api}")
    app_name = check_envvar_exists("APP_NAME")
    image_name = check_envvar_exists("IMAGE_NAME")

    @recipe(**recipe_kwargs)
    def service():
        with pushd(root_dir):
            _image = callable(image) and image() or image
            _env = callable(env) and env() or env
            try:
                if service_api == "base":
                    out = run([
                        kubectl_cmd, *kubectl_opts, "-n", namespace, "get", "deployments",
                        "-o", "jsonpath=\"{{.items[?(@.metadata.name=='{}')]}}\"".format(app_name)
                    ], check=True, capture_output=True).stdout
                    if len(out) > len('""'):  # found
                        Help.log(f"updating deployment '{app_name}")
                        out = run([
                            kubectl_cmd, *kubectl_opts, "-n", namespace, "set", "image", f"deployment/{app_name}",
                            f"{image_name}={_image}", "--record"
                        ], check=True, capture_output=True).stdout
                        [Help.log(f"> {l}") for l in out.decode().splitlines()]
                    else:
                        Help.log(f"creating deployment '{app_name}")
                        out = run([
                            kn_cmd, *kubectl_opts, "-n", namespace, "create", "deployment", app_name,
                            "--image", _image
                        ], check=True, capture_output=True).stdout
                        [Help.log(f"> {l}") for l in out.decode().splitlines()]
                        Help.log("setting labels")
                        for label, value in labels.items():
                            out = run([
                                kubectl_cmd, *kubectl_opts, "-n", namespace, "label", "deployment", app_name,
                                "=".join([label, value.format(APP_NAME=app_name)])
                            ], check=True, capture_output=True).stdout
                        [Help.log(f"> {l}") for l in out.decode().splitlines()]
                        if service_type != "":
                            Help.log("creating service")
                            out = run([
                                kubectl_cmd, *kubectl_opts, "-n", namespace, "expose", "deployment", app_name,
                                "--type", service_type, "--protocol", "TCP", "--port", "80", "--target-port", "8080"
                            ], check=True, capture_output=True).stdout
                            [Help.log(f"> {l}") for l in out.decode().splitlines()]
                elif service_api == "knative":
                    out = run([
                        kn_cmd, *kn_opts, "-n", namespace, "service", "list",
                        "-o", "jsonpath=\"{{.items[?(@.metadata.name=='{}')].metadata.name}}\"".format(app_name)
                    ], check=True, capture_output=True).stdout
                    if out.decode().rstrip() == f'"{app_name}"':  # found
                        Help.log(f"updating existing knative service '{app_name}'")
                        out = run([
                            kn_cmd, *kn_opts, "-n", namespace, "service", "update", app_name,
                            "--image", _image,
                            "--revision-name", "{{.Service}}-{{.Random 5}}-{{.Generation}}"
                        ], check=True, capture_output=True).stdout
                        [Help.log(f"> {l}") for l in out.decode().splitlines()]
                    else:
                        Help.log(f"creating knative service {app_name}")

                        out = run([
                            kn_cmd, *kn_opts, "-n", namespace, "service", "create", app_name,
                            "--image", _image,
                            *list(
                                sum([
                                    ("--label", f"{name}={value.format(APP_NAME=app_name)}") for name, value in
                                    labels.items()
                                ], ())
                            ),
                            *list(
                                sum([
                                    ("--env", f"{name}={value}") for name, value in _env.items()
                                ], ())
                            ),
                            *kn_extra,
                        ], check=True, capture_output=True).stdout
                        [Help.log(f"> {l}") for l in out.decode().splitlines()]
            except CalledProcessError as err:
                Help.error(err.stderr.decode())


def make_clean_recipe(globs, on_completed=lambda: None, **recipe_kwargs):
    abs_path = os.path.abspath(inspect.stack()[-1].filename)
    root_dir = os.path.dirname(abs_path)

    if 'info' not in recipe_kwargs:
        recipe_kwargs['info'] = "Clean up project"

    @recipe(**recipe_kwargs)
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


def copy_dirs(dirs: typing.Iterable[str], dst: str, override=True):
    abs_path = os.path.abspath(inspect.stack()[1].filename)
    root_dir = os.path.dirname(abs_path)

    with pushd(root_dir):
        os.makedirs(dst, exist_ok=True)
        for p in dirs:
            to_path = os.path.join(dst, os.path.basename(p))
            if os.path.exists(to_path):
                if override:
                    shutil.rmtree(to_path)
                else:
                    Help.error(f"Destination path {to_path} already exists")
            shutil.copytree(p, to_path)
