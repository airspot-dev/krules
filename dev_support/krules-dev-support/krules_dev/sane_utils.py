import contextlib
import hashlib
import os

import yaml
import shutil
import typing
from glob import glob
from pathlib import Path
from subprocess import run, CalledProcessError

from dotenv import load_dotenv
from sane import *
from sane import _Help as Help


def check_env(name):
    if name not in os.environ:
        Help.error(f'Environment variable {name} does not exists')
    return os.environ[name]


def check_cmd(cmd):
    cmd = shutil.which(cmd)
    if cmd is None:
        Help.error(f'Command {cmd} not found in PATH')
    return cmd


def load_env():

    def _load_dir_env(_dir):
        for f in ("env.project", ".env", "env", ".env.local", "env.local"):
            load_dotenv(
                os.path.join(_dir, f)
            )
        for f in (".env.override", "env.override"):
            load_dotenv(
                os.path.join(_dir, f),
                override=True
            )

    # look for env files in caller directory
    abs_path = os.path.abspath(inspect.stack()[-1].filename)
    cur_dir = os.path.dirname(abs_path)

    # look for a project file
    p = Path(cur_dir)
    traversed_p = []
    while True:
        traversed_p.insert(0, p)
        is_project_dir = bool(sum(1 for x in p.glob("env.project")))
        is_root = p.parent == p
        if is_project_dir:
            os.environ["KRULES_PROJECT_DIR"] = str(p)
            break
        if is_root:
            break
        p = p.parent

    for p in traversed_p:
        Help.log("Loading environment for {}".format(p))
        _load_dir_env(p)




def get_buildable_image(location: str,
                        dir_name: str,
                        out_dir: str = ".build",
                        name=None,
                        use_release_version=True,
                        docker_registry=None,
                        environ_override: typing.Optional[str] = None,
                        push_cmd: str = "push",
                        digest_file: str = ".digest"):
    if environ_override is not None and environ_override in os.environ:
        return os.environ[environ_override]
    if use_release_version and 'RELEASE_VERSION' in os.environ:
        if docker_registry is None:
            docker_registry = check_env("DOCKER_REGISTRY")
        if name is None:
            name = f'krules-{dir_name}'
        return f'{docker_registry}/{name}:{os.environ["RELEASE_VERSION"]}'
    try:
        build_dir = os.path.join(location, dir_name)
        Help.log(f"Ensuring {os.path.join(out_dir, digest_file)} in {dir_name}")
        run([
            os.path.join(build_dir, "make.py"), push_cmd
        ], env={"PATH": os.environ["PATH"]}, capture_output=True, check=True)
        with open(os.path.join(build_dir, out_dir, digest_file), "r") as f:
            return f.read().strip()
    except CalledProcessError as ex:
        Help.error(ex.stdout.decode())


def get_image(image, environ_override: typing.Optional[str] = None):
    """
    Convenient method for guessing the image name if we have a RELEASE_VERSION defined
    or using the KRrules source repo located in KRULES_REPO_DIR.
    It is a wrapper for the more specialized get_buildable_image function
    """
    if "RELEASE_VERSION" in os.environ:
        docker_registry = check_env("RELEASE_DOCKER_REGISTRY")
        return get_buildable_image(
            location="",
            dir_name=image,
            environ_override=environ_override,
            docker_registry=docker_registry,
        )
    if "KRULES_REPO_DIR" in os.environ:
        return get_buildable_image(
            location=os.path.join(os.environ["KRULES_REPO_DIR"], "images"),
            dir_name=image,
            environ_override=environ_override,
        )
    if environ_override is not None and environ_override in os.environ:
        return os.environ[environ_override]
    Help.error("One of RELEASE_VERSION or KRULES_REPO_DIR needed")


def get_project_base(location):
    """
    Get and eventually build the image from the specified folder contained in the project root
    It is a wrapper for the more specialized get_buildable_image function

    :param location: a folder with that name is expected in the project root to build image from
    :return image digest
    """
    if "KRULES_PROJECT_DIR" not in os.environ:
        Help.error("Cannot guess project root directory")
    target_dir = os.path.join(os.environ["KRULES_PROJECT_DIR"], location)
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        Help.error(f"{target_dir} does not exists or is not a directory")
    return get_buildable_image(
        location=os.environ["KRULES_PROJECT_DIR"],
        dir_name=location,
        environ_override=None,
        use_release_version=False,
    )


def update_code_hash(globs: list,
                     out_dir: str = ".build",
                     output_file: str = ".code.digest"):

    abs_path = os.path.abspath(inspect.stack()[-1].filename)
    root_dir = os.path.dirname(abs_path)
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    files = []
    with pushd(root_dir):
        for file in globs:
            files.extend(glob(file, recursive=True))

        code_hash = hashlib.md5()
        for file in files:
            if os.path.isfile(file):
                code_hash.update(open(file, "rb").read())
        open(os.path.join(out_dir, output_file), "w").write(code_hash.hexdigest())


def make_render_resource_recipes(globs: list,
                                 out_dir: str = ".build",
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

        resource_file = os.path.join(out_dir, os.path.split(j2_template)[1].split(".j2")[0])
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
                Path(out_dir).mkdir(parents=True, exist_ok=True)
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
                      out_dir: str = ".build",
                      dockerfile: str = "Dockerfile",
                      code_digest_file: str = ".code.digest",
                      success_file: str = None,
                      build_args: dict = {},
                      **recipe_kwargs):
    abs_path = os.path.abspath(inspect.stack()[-1].filename)
    root_dir = os.path.dirname(abs_path)
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    if target is None:
        target = check_env('IMAGE_NAME')

    if 'name' not in recipe_kwargs:
        recipe_kwargs['name'] = 'build'
    docker_cmd = os.environ.get("DOCKER_CMD", check_cmd("docker"))
    if success_file is None:
        success_file = f".{recipe_kwargs['name']}.success"
    if 'info' not in recipe_kwargs:
        recipe_kwargs['info'] = "Build the docker image for target {target}"
    recipe_kwargs['info'] = recipe_kwargs['info'].format(target=target)

    if 'conditions' not in recipe_kwargs:
        recipe_kwargs['conditions'] = []
    success_file = os.path.join(root_dir, out_dir, success_file)
    code_digest_file = os.path.join(root_dir, out_dir, code_digest_file)
    recipe_kwargs['conditions'].append(lambda: not os.path.exists(success_file))
    recipe_kwargs['conditions'].append(lambda: os.path.exists(code_digest_file) and
                                               open(success_file).read() != open(code_digest_file).read())

    @recipe(**recipe_kwargs)
    def build():
        docker_registry = check_env('DOCKER_REGISTRY')
        check_cmd(docker_cmd)
        target_image = f'{docker_registry}/{target}'.lower()
        Help.log(f'Building {target_image} from Dockerfile')

        for func in run_before:
            Help.log(f"..executing {func.__name__}")
            func()

        with pushd(root_dir):
            _build_args = " ".join([f"--build-arg {v[0]}={v[1]}" for v in build_args.items()])
            try:
                out = run(
                    f'{docker_cmd} build -t {target_image} -f {os.path.join(out_dir, dockerfile)} {_build_args} .', shell=True,
                    check=True, capture_output=True
                ).stdout
                [Help.log(f"> {l}") for l in out.decode().splitlines()]
                with open(success_file, "w") as f:
                    try:
                        code_digest = open(code_digest_file, "r").read()
                    except FileNotFoundError:
                        code_digest = ""
                    f.write(code_digest)
            except CalledProcessError as ex:
                if os.path.exists(success_file):
                    os.unlink(success_file)
                Help.error(ex.stderr.decode())


def make_push_recipe(digest_file: str = ".digest",
                     out_dir: str = ".build",
                     tag: str = os.environ.get("RELEASE_VERSION"),
                     target: str = None,
                     run_before: typing.Sequence[typing.Callable] = (),
                     dependent_build_recipe: str = "build",
                     **recipe_kwargs):
    abs_path = os.path.abspath(inspect.stack()[-1].filename)
    root_dir = os.path.dirname(abs_path)
    docker_cmd = os.environ.get("DOCKER_CMD", check_cmd("docker"))
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    if 'name' not in recipe_kwargs:
        recipe_kwargs['name'] = "push"

    if target is None:
        target = os.environ.get('IMAGE_NAME')

    docker_registry = os.environ.get('DOCKER_REGISTRY')
    target_image = f"{docker_registry}/{target}".lower()

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
        check_env("IMAGE_NAME")
        check_env("DOCKER_REGISTRY")

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
                with open(os.path.join(out_dir, digest_file), "wb") as f:
                    f.write(out)
            except CalledProcessError as ex:
                Help.error(ex.stderr.decode())


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


def make_service_recipe(image: typing.Union[str, typing.Callable] = None,
                        out_dir: str = ".build",
                        labels: typing.Union[dict, typing.Callable] = {},
                        service_account: str = None,
                        kn_extra: tuple = (),
                        env: typing.Union[dict, typing.Callable[[], dict]] = {},
                        **recipe_kwargs):
    abs_path = os.path.abspath(inspect.stack()[-1].filename)
    root_dir = os.path.dirname(abs_path)
    namespace = check_env("NAMESPACE")
    service_api = os.environ.get("SERVICE_API", "base")
    service_type = os.environ.get("SERVICE_TYPE", "ClusterIP")
    kubectl_cmd = kubectl_opts = kn_cmd = kn_opts = None
    if service_api == "base":
        kubectl_cmd = os.environ.get("KUBECTL_CMD", check_cmd("kubectl"))
        kubectl_opts = os.environ.get("KUBECTL_OPTS", "").split()
    elif service_api == "knative":
        kn_cmd = os.environ.get("KN_CMD", check_cmd("kn"))
        kn_opts = os.environ.get("KN_OPTS", "").split()
    else:
        Help.error(f"unknown service api {service_api}")
    app_name = check_env("APP_NAME")

    @recipe(**recipe_kwargs)
    def service():
        # image_name = check_envvar_exists("IMAGE_NAME")

        with pushd(root_dir):
            #print(f"*********> {root_dir}")
            _image = callable(image) and image() or image
            if _image is None:
                _image = open(os.path.join(out_dir, ".digest"), "r").read().rstrip()
            _env = callable(env) and env() or env
            _labels = callable(labels) and labels() or labels
            try:
                if service_api == "base":
                    out = run([
                        kubectl_cmd, *kubectl_opts, "-n", namespace, "get", "deployments",
                        "-o", "jsonpath=\"{{.items[?(@.metadata.name=='{}')]}}\"".format(app_name)
                    ], check=True, capture_output=True).stdout
                    if len(out) > len('""'):  # found
                        Help.log(f"updating deployment {app_name}")
                        out = run([
                            kubectl_cmd, *kubectl_opts, "-n", namespace, "set", "image", f"deployment/{app_name}",
                            f"{app_name}={_image}", "--record"
                        ], check=True, capture_output=True).stdout
                        [Help.log(f"> {l}") for l in out.decode().splitlines()]
                    else:
                        Help.log(f"creating deployment {app_name}")
                        deployment = {
                            "apiVersion": "apps/v1",
                            "kind": "Deployment",
                            "metadata": {
                                "name": app_name,
                                "labels": _labels,
                            },
                            "spec": {
                                "replicas": 1,  # TODO: env var
                                "selector": {
                                    "matchLabels": _labels,
                                },
                                "template": {
                                    "metadata": {
                                        "labels": _labels,
                                    },
                                    "spec": {
                                        "containers": [
                                            {
                                                "name": app_name,
                                                "image": _image,
                                                "env": [{"name": e[0], "value": e[1]} for e in _env.items()],
                                                "ports": [
                                                    {
                                                        "containerPort": 8080,
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                        if service_account:
                            deployment["spec"]["template"]["spec"]["serviceAccountName"] = service_account
                        out = run([
                            kubectl_cmd, *kubectl_opts, "-n", namespace, "apply", "-f", "-",
                        ], input=yaml.dump(deployment, Dumper=yaml.SafeDumper).encode("utf-8"), check=True, capture_output=True).stdout
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
                        service_account_args = ()
                        if service_account:
                            service_account_args = ("--service-account", service_account)
                        out = run([
                            kn_cmd, *kn_opts, "-n", namespace, "service", "create", app_name,
                            "--image", _image,
                            *list(
                                sum([
                                    ("--label", f"{name}={value.format(APP_NAME=app_name)}") for name, value in
                                    _labels.items()
                                ], ())
                            ),
                            *list(
                                sum([
                                    ("--env", f"{name}={value}") for name, value in _env.items()
                                ], ())
                            ),
                            *service_account_args,
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


def copy_resources(src: typing.Iterable[str], dst: str,
                   override: bool = True,
                   make_recipes_before: typing.Iterable = (),
                   make_recipes_after: typing.Iterable = (),
                   workdir: str = None):

    for recipe in make_recipes_before:
        for f in src:
            fname=os.path.basename(f)
            fdir=os.path.dirname(f)
            make_py = os.path.join(fdir, "make.py")
            if os.path.exists(make_py):
                cmd = " ".join((make_py, recipe.format(src=fname)))
                Help.log(f"Invoking [before] {cmd}")
                try:
                    run(cmd, shell=True, check=True, capture_output=True)
                except CalledProcessError as err:
                    Help.error(err.stderr.decode())

    if workdir is None:
        workdir = os.path.abspath(inspect.stack()[1].filename)
    dest_dir = os.path.dirname(workdir)

    # wi pushd(src_base_dir):
    #       _recipe_before:
    #         run(f"make
    #         y {r)}", shell=True, check=True, capture_output=True)
    with pushd(dest_dir):
        os.makedirs(dst, exist_ok=True)
        for p in src:
            to_path = os.path.join(dst, os.path.basename(p))
            if os.path.exists(to_path):
                if override:
                    if os.path.isdir(to_path):
                        shutil.rmtree(to_path)
                    else:
                        os.unlink(to_path)
                else:
                    Help.error(f"Destination path {to_path} already exists")
            if os.path.isdir(p):
                shutil.copytree(p, to_path)
            else:
                shutil.copyfile(p, to_path)
            for recipe in make_recipes_after:
                make_py = os.path.join(to_path, "make.py")
                if os.path.exists(make_py):
                    cmd = " ".join((make_py, recipe))
                    Help.log(f"Invoking [after] {cmd}")
                    try:
                        run(cmd, shell=True, check=True, capture_output=True)
                    except CalledProcessError as err:
                        Help.error(err.stderr.decode())


# TODO: unused? -- remove?
def make_copy_resources_recipe(src: typing.Union[typing.Iterable[str], str],
                               dst: str,
                               render_first: bool,
                               **recipe_kwargs):
    make_recipes_before = []
    if render_first:
        make_recipes_before.append('{src}')

    if 'name' not in recipe_kwargs:
        Help.error("You must provide a name for copy resources recipe")

    workdir = os.path.abspath(inspect.stack()[1].filename)

    @recipe(**recipe_kwargs)
    def _recipe():
        copy_resources(
                src=src,
                dst=".",
                make_recipes_before=make_recipes_before,
                workdir=workdir
            )


def copy_source(src: typing.Union[typing.Iterable[str], str],
                dst: str,
                override: bool = True,
                make_recipes: typing.Iterable = ("clean", "setup.py"),
                workdir: str = None):
    """
    It assumes paths relative to KRULES_REPO_DIR
    :param src: 
    :param dst: 
    :param condition: 
    :param override: 
    :param make_recipes: 
    :param workdir:
    :return:
    """
    if isinstance(src, str):
        src = [src]
    #src = list(map(lambda x: os.path.join(check_env("KRULES_REPO_DIR"), x), src))

    if workdir is None:
        workdir = os.path.abspath(inspect.stack()[1].filename)
    copy_resources(
        src, dst, override, make_recipes_before=(), make_recipes_after=make_recipes,
        workdir=workdir,
    )

def make_copy_source_recipe(location: str,
                            src: typing.Union[typing.Iterable[str], str],
                            dst: str,
                            out_dir: str = ".build",
                            override: bool = True,
                            make_recipes: typing.Iterable = ("clean", "setup.py"),
                            workdir: str = None,
                            **recipe_kwargs):
    src = list(map(lambda x: os.path.join(location, x), src))
    if workdir is None:
        workdir = os.path.abspath(inspect.stack()[1].filename)
    @recipe(**recipe_kwargs)
    def _recipe():
        copy_source(
            src=src,
            dst=os.path.join(out_dir, dst),
            override=override,
            make_recipes=make_recipes,
            workdir=workdir,
        )


def make_subprocess_run_recipe(cmd, **recipe_kwargs):

    if 'name' not in recipe_kwargs:
        Help.error("You must provide a name for subprocess run recipe")

    @recipe(**recipe_kwargs)
    def _recipe():
        run_kwargs = {"check": True, "capture_output": True}
        if isinstance(cmd, str):
            run_kwargs["shell"] = True
        out = run(
            cmd, **run_kwargs
        ).stdout
        [Help.log(f"> {l}") for l in out.decode().splitlines()]
