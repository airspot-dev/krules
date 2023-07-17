import contextlib
import hashlib
import io
import re
import sys
import os
import inspect

import yaml
import shutil
import typing
from glob import glob
from pathlib import Path
from subprocess import CalledProcessError
import subprocess

from dotenv import load_dotenv
from sane import recipe as base_recipe
from sane import _Help as Help
import sh

import logging

logger = logging.getLogger("__sane__")
logger.setLevel(int(os.environ.get("SANE_LOG_LEVEL", logging.INFO)))
logger.handlers[0].setLevel(int(os.environ.get("SANE_LOG_LEVEL", logging.INFO)))

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars, unbind_contextvars

log = structlog.get_logger()


def recipe(*args, name=None, hooks=[], recipe_deps=[],
           hook_deps=[], conditions=[], info=None, **kwargs):
    #frame = inspect.stack(context=3)[-1]

    # `frame` is disposed of once used

    # class _wrapper():
    #
    #     def __init__(self, fn):
    #         self._fn = fn
    #
    #     def __call__(self, *args, **kwargs):
    #         print("before")
    #         self._fn(*args, **kwargs)
    #         print("after")


    def recipe_fn(fn):
        #import pdb; pdb.set_trace()
        nonlocal name
        if name is None:
            name = fn.__name__

        base_recipe(
            *args, name=name, hooks=hooks, recipe_deps=recipe_deps,
            hook_deps=hook_deps, conditions=conditions, info=info, **kwargs)(wrap(fn))
        # from sane import _stateful
        # _stateful.register_decorator_call(*args, frame=frame, name=name,
        #                                   hooks=hooks, recipe_deps=recipe_deps,
        #                                   hook_deps=hook_deps,
        #                                   conditions=conditions,
        #                                   info=info, fn=wrap(fn), **kwargs)
        # r_func(fn)
        return fn


    def wrap(fn):
        def __wrapped__():
            bind_contextvars(
                recipe=name,
            )
            fn()
            unbind_contextvars("recipe")

        __wrapped__.__name__=fn.__name__
        return __wrapped__



    return recipe_fn


def check_env(name, err_code=-1):
    if name not in os.environ:
        log.error(f'Environment variable does not exists', name=name)
        sys.exit(err_code)
    return os.environ[name]


def check_cmd(cmd: str, err_code=-1):
    _cmd = os.environ.get(f"{cmd.upper()}_CMD") or shutil.which(cmd)
    if _cmd is None:
        log.error(f'Command not found', cmd=cmd, PATH=os.environ.get("PATH"))
        sys.exit(err_code)
    return _cmd


def _run(cmd: str | list, env=None, err_to_stdout=False, check=True, errors_log_level=logging.ERROR, captures={}):

    log.warning("!!!RUN FUNCTION DEPRECATED!!!", cmd=cmd)

    def __log_out(message):
        prev_stream = logger.handlers[0].stream
        logger.handlers[0].stream = sys.stdout
        logger.info(message)
        logger.handlers[0].stream = prev_stream

    def __log_err(message):
        prev_stream = logger.handlers[0].stream
        if err_to_stdout:
            logger.handlers[0].stream = sys.stdout
        else:
            logger.handlers[0].stream = sys.stderr
        logger.log(errors_log_level, message)
        logger.handlers[0].stream = prev_stream

    shell = isinstance(cmd, str)
    log_out = __log_out
    log_err = __log_err
    if shell:
        log_prefix = os.path.basename(cmd.split()[0])
    else:
        log_prefix = os.path.basename(cmd[0])
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, shell=shell)
    for c in iter(lambda: p.stdout.readline(), b""):
        message = c.decode('utf-8')
        if "stdout" in captures:
            captures["stdout"].append(message)
        log_out(f"{log_prefix}> {message}")
    for c in iter(lambda: p.stderr.readline(), b""):
        message = c.decode('utf-8')
        if "stderr" in captures:
            captures["stderr"].append(message)
        log_err(f"{log_prefix}> {message}")
    p.communicate()
    if check and p.returncode != 0:
        sys.exit(p.returncode)
    return p.returncode


def _sh(cmd: str | list, env=None, err_to_stdout=False, check=True, errors_log_level=logging.ERROR, captures={}):
    if isinstance(cmd, str):
        cmd = cmd.split(" ")
    sh.bash(*cmd)


def get_targets_info():
    target = os.environ.get("TARGET", os.environ.get("DEFAULT_TARGET", "default"))
    targets = [s.lower() for s in re.split(" |,|;", os.environ.get("TARGETS", "default")) if len(s)]

    if target not in targets:
        log.error("Unknown target", target=target, targets=targets)
        sys.exit(-1)

    return target, targets

def load_env():

    def _load_dir_env(_dir):
        for f in ("env.project", ".env", "env", ".env.local", "env.local"):
            p = os.path.join(_dir, f)
            if os.path.exists(p):
                log.debug("Loading environment", file=p)
                load_dotenv(p)
        for f in (".env.override", "env.override"):
            p = os.path.join(_dir, f)
            if os.path.exists(p):
                log.debug("Overriding environment", file=p)
                load_dotenv(p, override=True)

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
        _load_dir_env(p)


def get_buildable_image(location: str,
                        dir_name: str,
                        out_dir: str = ".build",
                        name=None,
                        use_release_version=True,
                        docker_registry=None,
                        environ_override: typing.Optional[str] = None,
                        push_cmd: str = "push",
                        digest_file: str = ".digest",
                        target: str = os.environ.get("TARGET", "default")):
    if environ_override is not None and environ_override in os.environ:
        return os.environ[environ_override]
    if use_release_version and 'RELEASE_VERSION' in os.environ:
        if docker_registry is None:
            docker_registry = get_var_for_target("DOCKER_REGISTRY", target=target)
        if name is None:
            name = f'krules-{dir_name}'
        return f'{docker_registry}/{name}:{os.environ["RELEASE_VERSION"]}'
    build_dir = os.path.join(location, dir_name)
    log.debug("Checking digest file", out_dir=out_dir, digest_file=digest_file, dir_name=dir_name)
    #log.debug(f"Ensuring {os.path.join(out_dir, digest_file)} in {dir_name}")
    make = sh.Command(
        check_cmd("python"),
    ).bake(os.path.join(build_dir, "make.py"))
    try:
        env = os.environ.copy()
        env.pop("IMAGE_NAME", None)
        make(push_cmd, _env=env)
    except sh.ErrorReturnCode as ex:
        log.error(ex.stderr.decode())
        sys.exit(-1)
    with open(os.path.join(build_dir, out_dir, digest_file), "r") as f:
        return f.read().strip()
    # ret_code = _run([
    #     os.path.join(build_dir, "make.py"), push_cmd
    # ], env={"PATH": os.environ["PATH"]}, check=False)
    # if ret_code == 0:
    #     with open(os.path.join(build_dir, out_dir, digest_file), "r") as f:
    #         return f.read().strip()
    # else:
    #     logger.error(f"Unable to push image : {docker_registry}/{name}")

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
    logger.error("One of RELEASE_VERSION or KRULES_REPO_DIR needed")


def get_project_base(location):
    """
    Get and eventually build the image from the specified folder contained in the project root
    It is a wrapper for the more specialized get_buildable_image function

    :param location: a folder with that name is expected in the project root to build image from
    :return image digest
    """
    if "KRULES_PROJECT_DIR" not in os.environ:
        logger.error("Cannot guess project root directory")
    target_dir = os.path.join(os.environ["KRULES_PROJECT_DIR"], location)
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        logger.error(f"{target_dir} does not exists or is not a directory")
    return get_buildable_image(
        location=os.environ["KRULES_PROJECT_DIR"],
        dir_name=location,
        environ_override=None,
        use_release_version=False,
    )


def update_code_hash(globs: list,
                     out_dir: str = ".build",
                     output_file: str = ".code.digest"):

    def _update_hash_within_dir(dir_path):
        for filename in os.listdir(dir_path):
            f = os.path.join(dir_path, filename)
            if os.path.isfile(f):
                code_hash.update(open(f, "rb").read())
            else:
                _update_hash_within_dir(f)

    abs_path = os.path.abspath(inspect.stack()[-1].filename)
    root_dir = os.path.dirname(abs_path)
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    files = []
    with pushd(root_dir):
        for file in globs:
            files.extend(glob(file, recursive=True))

        code_hash = hashlib.md5()
        for path in files:
            if os.path.isfile(path):
                code_hash.update(open(path, "rb").read())
            else:
                _update_hash_within_dir(path)
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
                log.debug(f"Rendering...", out_file=resource_file)
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


def make_build_recipe(image_name: str = None,
                      run_before: typing.Sequence[typing.Callable] = (),
                      out_dir: str = ".build",
                      dockerfile: str = "Dockerfile",
                      code_digest_file: str = ".code.digest",
                      success_file: str = None,
                      build_args: dict = {},
                      target: str = os.environ.get("TARGET", "default"),
                      **recipe_kwargs):
    abs_path = os.path.abspath(inspect.stack()[-1].filename)
    root_dir = os.path.dirname(abs_path)
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    if image_name is None:
        image_name = check_env('IMAGE_NAME')

    if 'name' not in recipe_kwargs:
        recipe_kwargs['name'] = 'build'
    docker_cmd = check_cmd("docker")
    if success_file is None:
        success_file = f".{recipe_kwargs['name']}.success"
    if 'info' not in recipe_kwargs:
        recipe_kwargs['info'] = "Build the docker image as {image_name}"
    recipe_kwargs['info'] = recipe_kwargs['info'].format(image_name=image_name)

    if 'conditions' not in recipe_kwargs:
        recipe_kwargs['conditions'] = []
    success_file = os.path.join(root_dir, out_dir, success_file)
    code_digest_file = os.path.join(root_dir, out_dir, code_digest_file)
    recipe_kwargs['conditions'].append(lambda: not os.path.exists(success_file))
    recipe_kwargs['conditions'].append(lambda: os.path.exists(code_digest_file) and
                                               open(success_file).read() != open(code_digest_file).read())

    @recipe(**recipe_kwargs)
    def build():
        docker_registry = get_var_for_target('DOCKER_REGISTRY', target=target, mandatory=True)
        target_image = f'{docker_registry}/{image_name}'.lower()
        log.debug("Building...", target_image=target_image)

        for func in run_before:
            log.debug(f"..executing run_before", func=func.__name__)
            func()

        with pushd(root_dir):
            #_build_args = " ".join([f"--build-arg {v[0]}={v[1]}" for v in build_args.items()])

            build_platform=get_var_for_target("BUILD_PLATFORM", target=target, default="amd64")

            docker=sh.Command(docker_cmd)

            try:
                try:
                    docker.build(
                        "--platform", build_platform,
                        "-t", target_image, "-f", os.path.join(out_dir, dockerfile),
                        *[item for row in [("--build-arg", f"{v[0]}={v[1]}") for v in build_args.items()] for item in row],
                        ".",
                        _tee='err',
                    )
                except sh.ErrorReturnCode as ex:
                    log.error(ex.stderr.decode())
                    sys.exit(ex.exit_code)

                with open(success_file, "w") as f:
                    try:
                        code_digest = open(code_digest_file, "r").read()
                    except FileNotFoundError:
                        code_digest = ""
                    f.write(code_digest)

                log.info("Built image", target_image=target_image)

            except sh.ErrorReturnCode as ex:
                if os.path.exists(success_file):
                    os.unlink(success_file)
                log.error(f"Unable to build image", target_image=target_image)
                raise ex




def make_push_recipe(digest_file: str = ".digest",
                     out_dir: str = ".build",
                     tag: str = os.environ.get("RELEASE_VERSION"),
                     image_name: str = None,
                     run_before: typing.Sequence[typing.Callable] = (),
                     dependent_build_recipe: str = "build",
                     target: str = os.environ.get("TARGET", "default"),
                     **recipe_kwargs):
    abs_path = os.path.abspath(inspect.stack()[-1].filename)
    root_dir = os.path.dirname(abs_path)
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    if 'name' not in recipe_kwargs:
        recipe_kwargs['name'] = "push"

    if image_name is None:
        image_name = check_env('IMAGE_NAME')

    docker_registry = get_var_for_target('DOCKER_REGISTRY', target=target, mandatory=True)
    target_image = f"{docker_registry}/{image_name}".lower()

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

        for func in run_before:
            func()

        log.debug(f'Pushing...', tag=_tag)

        with pushd(root_dir):
            docker = sh.Command(check_cmd("docker"))
            if tag:
                docker.tag(
                    target_image, tag
                )
            docker.push(_tag)
            of = os.path.join(out_dir, digest_file)
            with open(of, "wb") as f:
                docker.inspect(
                    f'--format="{{{{index .RepoDigests 0}}}}"',
                    _tag,
                    _out=f,
                )
            log.info("Pushed", digest=open(of, "r").read())


def make_apply_recipe(globs: typing.Iterable[str], run_before: typing.Iterable[typing.Callable] = (), context=None,
                      **recipe_kwargs):
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
        kubectl_opts = os.environ.get("KUBECTL_OPTS", "").split()
        context_opt = None
        context_idx = -1
        if context is not None:
            for idx, opt in enumerate(kubectl_opts):
                if opt.startswith("--context="):
                    context_opt = opt
                    context_idx = idx
                    break
            if context_opt is not None:
                kubectl_opts[context_idx] = f"--context={context}"
            else:
                kubectl_opts.append(f"--context={context}")
        for func in run_before:
            func()
        with pushd(root_dir):
            k8s_files = []
            for file in globs:
                k8s_files.extend(glob(file))
            for file in sorted(k8s_files):
                logger.info(f"Applying {file}..")
                ret_code = _run(
                    [
                        kubectl_cmd, *kubectl_opts,  "apply", "-f", file,
                    ],
                    check=False
                )
                if ret_code != 0:
                    logger.error(f"Unable to apply {file}")


def make_service_recipe(image: typing.Union[str, typing.Callable] = None,
                        out_dir: str = ".build",
                        labels: typing.Union[dict, typing.Callable] = {},
                        service_account: str = None,
                        kn_extra: tuple = (),
                        env: typing.Union[dict, typing.Callable[[], dict]] = {},
                        context=None,
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
        context_opt = None
        context_idx = -1
        if context is not None:
            for idx, opt in enumerate(kubectl_opts):
                if opt.startswith("--context="):
                    context_opt = opt
                    context_idx = idx
                    break
            if context_opt is not None:
                kubectl_opts[context_idx] = f"--context={context}"
            else:
                kubectl_opts.append(f"--context={context}")
    elif service_api == "knative":
        kn_cmd = os.environ.get("KN_CMD", check_cmd("kn"))
        kn_opts = os.environ.get("KN_OPTS", "").split()
    else:
        logger.error(f"unknown service api {service_api}")
        sys.exit(-1)
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
                    out = subprocess.run([
                        kubectl_cmd, *kubectl_opts, "-n", namespace, "get", "deployments",
                        "-o", "jsonpath=\"{{.items[?(@.metadata.name=='{}')]}}\"".format(app_name)
                    ], check=True, capture_output=True).stdout
                    if len(out) > len('""'):  # found
                        logger.info(f"updating deployment {app_name}")
                        ret_code = _run([
                            kubectl_cmd, *kubectl_opts, "-n", namespace, "set", "image", f"deployment/{app_name}",
                            f"{app_name}={_image}", "--record"
                        ])
                        if ret_code != 0:
                            logger.error(f"Unable to update Deployment: {app_name}")
                    else:
                        logger.info(f"creating deployment {app_name}")
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
                        out = subprocess.run([
                            kubectl_cmd, *kubectl_opts, "-n", namespace, "apply", "-f", "-",
                        ], input=yaml.dump(deployment, Dumper=yaml.SafeDumper).encode("utf-8"), check=True, capture_output=True).stdout
                        [logger.info(f"> {l}") for l in out.decode().splitlines()]
                        if service_type != "":
                            logger.info("creating service")
                            ret_code = _run([
                                kubectl_cmd, *kubectl_opts, "-n", namespace, "expose", "deployment", app_name,
                                "--type", service_type, "--protocol", "TCP", "--port", "80", "--target-port", "8080"
                            ])
                            if ret_code != 0:
                                logger.error(f"Unable to create Service: {app_name}")
                elif service_api == "knative":
                    out = subprocess.run([
                        kn_cmd, *kn_opts, "-n", namespace, "service", "list",
                        "-o", "jsonpath=\"{{.items[?(@.metadata.name=='{}')].metadata.name}}\"".format(app_name)
                    ], check=True, capture_output=True).stdout
                    if out.decode().rstrip() == f'"{app_name}"':  # found
                        logger.info(f"updating existing knative service '{app_name}'")
                        ret_code = _run([
                            kn_cmd, *kn_opts, "-n", namespace, "service", "update", app_name,
                            "--image", _image,
                            "--revision-name", "{{.Service}}-{{.Random 5}}-{{.Generation}}"
                        ])
                        if ret_code != 0:
                            logger.error(f"Unable to update Knative Service: {app_name}")
                    else:
                        logger.info(f"creating knative service {app_name}")
                        service_account_args = ()
                        if service_account:
                            service_account_args = ("--service-account", service_account)
                        ret_code = _run([
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
                        ])
                        if ret_code != 0:
                            logger.error(f"Unable to create Knative service: {app_name}")
            except CalledProcessError as err:
                logger.error(err.stderr.decode())


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
                if os.path.isdir(f):
                    log.debug(f"Cleaning...", directory=f)
                    shutil.rmtree(f)
                else:
                    log.debug(f"Cleaning...", file=f)
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
                   #make_recipes_before: typing.Iterable = (),
                   make_recipes_hooks: typing.Iterable = (),
                   workdir: str = None):

    # for recipe in make_recipes_before:
    #     for f in src:
    #         fname=os.path.basename(f)
    #         fdir=os.path.dirname(f)
    #         make_py = os.path.join(fdir, "make.py")
    #         if os.path.exists(make_py):
    #             cmd = " ".join((make_py, recipe.format(src=fname)))
    #             logger.info(f"Invoking [before] {cmd}")
    #             _run(cmd)

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
            if p.endswith("/"):
                p = p[:-1]
            basename = os.path.basename(p)
            if basename in ("", "."):
                continue
            to_path = os.path.join(dst, basename)
            if os.path.exists(to_path):
                if override:
                    if os.path.isdir(to_path):
                        #log.debug("Removing...", directory=to_path, override=override)
                        shutil.rmtree(to_path)
                    else:
                        #log.debug("Removing...", file=to_path, override=override)
                        os.unlink(to_path)
                else:
                    log.error(f"Destination path already exists", path=to_path)
                    sys.exit(-1)
            if os.path.isdir(p):
                log.debug("Copying...", directory=p, to_path=to_path, override=override)
                shutil.copytree(p, to_path)
            else:
                log.debug("Copying...", file=p, to_path=to_path, override=override)
                shutil.copyfile(p, to_path)
            for recipe in make_recipes_hooks:
                make_py = os.path.join(to_path, "make.py")
                log.debug("Hook recipe", make=make_py, hooked=recipe)
                if os.path.exists(make_py):
                    make = sh.Command("python").bake(make_py)
                    make(recipe)


# def make_copy_resources_recipe(src: typing.Union[typing.Iterable[str], str],
#                                dst: str,
#                                render_first: bool,
#                                **recipe_kwargs):
#     make_recipes_before = []
#     if render_first:
#         make_recipes_before.append('{src}')
#
#     if 'name' not in recipe_kwargs:
#         logger.error("You must provide a name for copy resources recipe")
#         sys.exit(-1)
#
#     workdir = os.path.abspath(inspect.stack()[1].filename)
#
#     @recipe(**recipe_kwargs)
#     def _recipe():
#         copy_resources(
#                 src=src,
#                 dst=".",
#                 make_recipes_before=make_recipes_before,
#                 workdir=workdir
#             )


def copy_source(src: typing.Union[typing.Iterable[str], str],
                dst: str,
                override: bool = True,
                #make_recipes: typing.Iterable = ("clean", "setup.py"),
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
        src, dst, override, #make_recipes_before=(), make_recipes_after=make_recipes,
        workdir=workdir,
    )


def make_copy_source_recipe(location: str,
                            src: typing.Union[typing.Iterable[str], str],
                            dst: str,
                            out_dir: str = ".build",
                            override: bool = True,
                            #make_recipes: typing.Iterable = ("clean", "setup.py"),
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
            #make_recipes=make_recipes,
            workdir=workdir,
        )


def make_subprocess_run_recipe(cmd, **recipe_kwargs):

    if 'name' not in recipe_kwargs:
        logger.error("You must provide a name for subprocess run recipe")
        sys.exit(-1)

    @recipe(**recipe_kwargs)
    def _recipe():
        _run(cmd)


def get_var_for_target(name: str, target: str, mandatory: bool = False, default=None) -> str | None:
    name = name.upper()
    target = target.upper()
    #log_msg = "Got variable for target"
    var_name = f"{target}_{name}"
    if var_name in os.environ:
        var_name = f"{target}_{name}"
        value = os.environ[var_name]
        #log.debug(log_msg, name=name, var_name=var_name, target=target)
        return value
    if name in os.environ:
        #log.debug(log_msg, name=name, var_name=name, target=target)
        return os.environ[name]
    else:
        if mandatory:
            log.error(f"missing required environment variable", name=name)
            sys.exit(-1)
    #log.debug("Got default variable for target", name=name, default=default)
    return default


def get_target_dicts(targets: typing.Iterable, keys: typing.Iterable[str | list | tuple]) -> list[dict]:
    ret: list[dict] = []
    for target in targets:
        dd = {
            "name": target
        }
        for k in keys:
            default: str | typing.Callable[[str], str] = ""
            if isinstance(k, (list, tuple)):
                k, default = k
            val = os.environ.get(f"{target.upper()}_{k.upper()}")
            if val is None:
                val = os.environ.get(f"{k.upper()}")
            if val is None:
                val = callable(default) and default(target) or default
            dd[k] = val

        ret.append(dd)
    return ret


def make_run_terraform_recipe(manifests_dir="terraform", init_params=(), **recipe_kwargs):

    @recipe(info="Apply terraform manifests", **recipe_kwargs)
    def run_terraform():
        terraform = check_cmd(os.environ.get("TERRAFORM_CMD", "terraform"))
        with pushd(manifests_dir):
            logger.info("Applying terraform manifests...")
            _run(f"{terraform} init --upgrade {' '.join(init_params)}")
            _run(f"{terraform} plan -out=terraform.tfplan")
            _run(f"{terraform} apply -auto-approve terraform.tfplan")
