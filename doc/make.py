#!/usr/bin/env python
from glob import glob
import subprocess
import shutil
import os

try:
    from krules_dev import sane_utils
except ImportError:
    print('\033[91mkrules local development support is not installed... run "pip install krules-dev-support"\033[0m')
    exit(-1)

from sane import *
from sane import _Help as Help


KRULES_ROOT_DIR = os.environ.get("KRULES_ROOT_DIR", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                 os.path.pardir))
KRULES_LIBS_DIR = os.path.join(KRULES_ROOT_DIR, "libs")

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
SOURCE_DIR = os.path.join(ROOT_DIR, "source")
BUILD_DIR = os.path.join(ROOT_DIR, "build")
ENV_DIR = os.path.join(ROOT_DIR, ".env")
RELEASE_VERSION = os.environ.get("RELEASE_VERSION")


sane_utils.make_render_resource_recipes(
    root_dir=ROOT_DIR,
    globs=[os.path.join("source", "conf.py.j2")],
    context_vars={
        "release_version": RELEASE_VERSION
    },
    run_before=[
        lambda: sane_utils.check_env("RELEASE_VERSION")
    ],
    hooks=["source_config"]
)


@recipe(
    info="Prepare virtual environment",
    conditions=[
        lambda: not os.path.exists(ENV_DIR)
    ],
    hook_deps=["source_config"]
)
def env():
    Help.log("creating virtualenv...")
    subprocess.run([
        "python3", "-m", "venv", ".env"
    ])
    subprocess.run([
        os.path.join(ENV_DIR, "bin", "pip3"), "install", "--upgrade", "pip", "setuptools"
    ])
    subprocess.run([
        os.path.join(ENV_DIR, "bin", "pip3"), "install", "--no-cache-dir", "-r", "requirements.txt"
    ])
    subprocess.run([
        os.path.join(ENV_DIR, "bin", "python3"), os.path.join(KRULES_LIBS_DIR, "krules-core", "setup.py"), "develop",
    ])
    subprocess.run([
        os.path.join(ENV_DIR, "bin", "python3"), os.path.join(KRULES_LIBS_DIR, "krules-k8s-functions", "setup.py"),
        "develop"
    ])


@recipe(
    info="Build multiversion documentation",
    conditions=[
        lambda: not os.path.exists(BUILD_DIR) or Help.file_condition(
            sources=glob(os.path.join(SOURCE_DIR, "*")),
            targets=[BUILD_DIR]
        )
    ],
    hook_deps=["source_config"],
    recipe_deps=[env]
)
def html():
    subprocess.run([os.path.join(ENV_DIR, "bin", "sphinx-build"), "-M", "html", SOURCE_DIR,
                    os.path.join(BUILD_DIR, "html", "en")])


@recipe(
    info="Build multiversion documentation",
    conditions=[
        lambda: not os.path.exists(BUILD_DIR) or Help.file_condition(
            sources=glob(os.path.join(SOURCE_DIR, "*")),
            targets=[BUILD_DIR]
        )
    ],
    hook_deps=["source_config"],
    recipe_deps=[env]
)
def multiversion():
    subprocess.run([os.path.join(ENV_DIR, "bin", "sphinx-multiversion"), SOURCE_DIR,
                    os.path.join(BUILD_DIR, "html", "en")])


sane_utils.make_clean_recipe(
    root_dir=ROOT_DIR,
    globs=["build", os.path.join("source", "conf.py")]
)


@recipe(info="Clean virtualenv")
def clean_env():
    if os.path.exists(ENV_DIR):
        shutil.rmtree(ENV_DIR)


sane_run(default=html)
