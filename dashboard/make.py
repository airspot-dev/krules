#!/usr/bin/env python
import os
import shutil
import typing
from glob import glob
from subprocess import run, CalledProcessError, CompletedProcess

from dotenv import load_dotenv

from krules_dev.sane_utils import check_cmd, check_envvar_exists

try:
    from krules_dev import sane_utils
except ImportError:
    print('\033[91mkrules-dev is not installed... run "pip install krules-dev"\033[0m')
    exit(-1)

from sane import *
from sane import _Help as Help


ROOT_DIR = os.path.dirname(os.path.realpath(__file__))

load_dotenv(
    os.path.join(ROOT_DIR, ".env")
)
load_dotenv(
    # local development (in .gitignore)
    os.path.join(ROOT_DIR, ".env.local")
)
load_dotenv(
    # override previously set (in .gitignore)
    os.path.join(ROOT_DIR, ".env.override"),
    override=True
)


DOCKER_CMD = os.environ.get("DOCKER_CMD", shutil.which("docker"))
KUBECTL_CMD = os.environ.get("KUBECTL_CMD", shutil.which("kubectl"))
KUBECTL_OPTS = os.environ.get("KUBECTL_OPTS", "")
KN_CMD = os.environ.get("KN_CMD", shutil.which("kn"))
KN_OPTS = os.environ.get("KN_OPTS", "")

RELEASE_VERSION = os.environ.get("RELEASE_VERSION")

KRULES_ROOT_DIR = os.environ.get("KRULES_ROOT_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir))
IMAGE_BASE = os.environ.get("IMAGE_BASE")

# DO NOT CHANGE SITE_NAME UNLESS YOU'VE CHANGED IT IN THE BASE IMAGE
SITE_NAME = os.environ.get("SITE_NAME", "sitebase")

APP_NAME = os.environ.get("APP_NAME", "dashboard")
IMAGE_NAME = os.environ.get("IMAGE_NAME", f"krules-django-{APP_NAME}")

CONFIGURATION_KEY = os.environ.get("CONFIGURATION_KEY", APP_NAME)

SERVICE_API = os.environ.get("SERVICE_API", "base")
SERVICE_TYPE = os.environ.get("SERVICE_TYPE", "")  # only for service api base (eg: ClusterIP, if "" service will not be created)
K_SINK = os.environ.get("K_SINK", "default")


def _get_image_base():
    global IMAGE_BASE, RELEASE_VERSION
    if IMAGE_BASE is not None:
        return IMAGE_BASE
    if IMAGE_BASE is None and RELEASE_VERSION is not None:
        IMAGE_BASE = f"krules-django-image-base:{RELEASE_VERSION}"
    else:
        run([os.path.join(KRULES_ROOT_DIR, "images", "django-image-base", "make.py")])
        with open(os.path.join(KRULES_ROOT_DIR, "images", "django-image-base", ".digest"), "r") as f:
            IMAGE_BASE = f.read().rstrip()
    return IMAGE_BASE

sane_utils.make_render_resource_recipes(
    ROOT_DIR,
    globs=[
        "*.j2",
    ],
    context_vars=lambda: {
        "image_base": _get_image_base(),
        "site_name": SITE_NAME,
        "app_name": APP_NAME,
        "configuration_key": CONFIGURATION_KEY,
    },
    hooks=['prepare_build']
)


sane_utils.make_build_recipe(
    name="build",
    root_dir=ROOT_DIR,
    docker_cmd=DOCKER_CMD,
    target=IMAGE_NAME,
    success_file=".build.success",
    out_file=".build.out",
    hook_deps=["prepare_build"],
)


sane_utils.make_push_recipe(
    name="push",
    root_dir=ROOT_DIR,
    docker_cmd=DOCKER_CMD,
    target=IMAGE_NAME,
    conditions=[
        Help.file_condition(
            sources=[os.path.join(ROOT_DIR, ".build.success")],
            targets=[os.path.join(ROOT_DIR, ".digest")]
        )
    ],
    digest_file=".digest",
    tag=RELEASE_VERSION,
    # run_before=[
    #     lambda: sane_run("build"),
    # ],
    recipe_deps=["build"],
)


sane_utils.make_render_resource_recipes(
    ROOT_DIR,
    globs=[
        "k8s/*.j2"
    ],
    context_vars=lambda: {
        "app_name": APP_NAME,
    },
    hooks=['prepare_deploy']
)


sane_utils.make_apply_recipe(
    name="apply",
    root_dir=ROOT_DIR,
    globs=["k8s/*.yaml"],
    kubectl_cmd=KUBECTL_CMD,
    recipe_deps=[],
    hook_deps=["prepare_deploy"],
    run_before=[
        #lambda: sane_run("push"),
        # lambda: [sane_run(x) for x in [
        #     "k8s/config-dashboard-site.yaml",
        #     "k8s/service.yaml",
        # ]]
    ]
)


@recipe(info="deploy service", recipe_deps=["push", "apply"])
def service():
    digest = open(".digest", "r").read().rstrip()
    [os.unlink(f) for f in glob(".deploy.out")]
    NAMESPACE = check_envvar_exists("NAMESPACE")
    try:
        if SERVICE_API == "base":
            check_cmd(KUBECTL_CMD)
            out = run([
                KUBECTL_CMD, *KUBECTL_OPTS.split(), "-n", NAMESPACE, "get", "deployments",
                "-o", "jsonpath=\"{{.items[?(@.metadata.name=='{}')]}}\"".format(APP_NAME)
            ], check=True, capture_output=True).stdout
            if len(out) > len('""'):  # found
                Help.log(f"updating deployment '{APP_NAME}")
                out = run([
                    KUBECTL_CMD, *KUBECTL_OPTS.split(), "-n", NAMESPACE, "set", "image", f"deployment/{APP_NAME}",
                    f"{IMAGE_NAME}={digest}", "--record"
                ], check=True, capture_output=True).stdout
                open(".deploy.out", "w").write(out.decode())
            else:
                Help.log(f"creating deployment '{APP_NAME}")
                with open(".deploy.out", "w") as fout:
                    out = run([
                        KUBECTL_CMD, *KUBECTL_OPTS.split(), "-n", NAMESPACE, "create", "deployment", APP_NAME,
                        "--image", digest
                    ], check=True, capture_output=True).stdout
                    fout.write(out.decode())
                    Help.log("seting label")
                    out = run([
                        KUBECTL_CMD, *KUBECTL_OPTS.split(), "-n", NAMESPACE, "label", "deployment", APP_NAME,
                        f"krules.airspot.dev/app={APP_NAME}"
                    ], check=True, capture_output=True).stdout
                    fout.write(out.decode())
                    if SERVICE_TYPE != "":
                        Help.log("creating service")
                        out = run([
                            KUBECTL_CMD, *KUBECTL_OPTS.split(), "-n", NAMESPACE, "expose", "deployment", APP_NAME,
                            "--type", SERVICE_TYPE, "--protocol", "TCP", "--port", "80", "--target-port", "8080"
                        ], check=True, capture_output=True).stdout
                        fout.write(out.decode())
        elif SERVICE_API == "knative":
            check_cmd(KN_CMD)
            out = run([
                KN_CMD, *KN_OPTS.split(), "-n", NAMESPACE, "service", "list",
                "-o", "jsonpath=\"{{.items[?(@.metadata.name=='{}')]}}\"".format(APP_NAME)
            ], check=True, capture_output=True).stdout
            if out.decode() == APP_NAME:  # found
                Help.log(f"updating existing knative service '{APP_NAME}'")
                out = run([
                    KN_CMD, *KN_OPTS.split(), "-n", NAMESPACE, "service", "update", APP_NAME,
                    "--image", digest
                ], check=True, capture_output=True).stdout
                open(".deploy.out", "w").write(out.decode())
            else:
                Help.log(f"creating knative service '{APP_NAME}")
                out = run([
                    KN_CMD, *KN_OPTS.split(), "-n", NAMESPACE, "service", "create", APP_NAME,
                    "--image", digest,
                    "--label", f"krules.airspot.dev/app={APP_NAME}"
                ], check=True, capture_output=True).stdout
                open(".deploy.out", "w").write(out.decode())
        else:
            Help.error(f"unknown service api {SERVICE_API}")
    except CalledProcessError as err:
        Help.error(err.stderr.decode())


sane_utils.make_clean_recipe(
    root_dir=ROOT_DIR,
    globs=["Dockerfile", "k8s/*.yaml", ".build.*", ".digest", ".deploy.out"]
)

sane_run("service")
