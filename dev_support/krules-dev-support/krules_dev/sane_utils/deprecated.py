import inspect
import logging
import os
import subprocess
import sys
import typing
from subprocess import CalledProcessError

import yaml

from krules_dev.sane_utils import check_env, check_cmd, logger, recipe, log, pushd


# used by vosk
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
        log.warning("!!!MAKE SERVICE RECIPE DEPRECATED!!!")
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


def make_subprocess_run_recipe(cmd, **recipe_kwargs):

    if 'name' not in recipe_kwargs:
        logger.error("You must provide a name for subprocess run recipe")
        sys.exit(-1)

    @recipe(**recipe_kwargs)
    def _recipe():
        _run(cmd)