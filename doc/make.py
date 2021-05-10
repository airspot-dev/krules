#!/usr/bin/env python
from glob import glob
import subprocess
import shutil
import os

try:
    from sane import *
    from sane import _Help as Help
except ImportError:
    from urllib.request import urlretrieve

    urlretrieve("https://raw.githubusercontent.com/mikeevmm/sane/master/sane.py", "sane.py")
    from sane import *
    from sane import _Help as Help

    Help.warn('sane.py downloaded locally.. "pip install sane-build" to make it globally available')

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
SOURCE_DIR = os.path.join(ROOT_DIR, "source")
BUILD_DIR = os.path.join(ROOT_DIR, "build")


@recipe(
    info="Build multiversion documentation",
    conditions=[
        Help.file_condition(
            sources=glob(os.path.join(SOURCE_DIR, "*")),
            targets=[BUILD_DIR]
        )
    ]
)
def html():
    Help.log("Building documentation..")
    if shutil.which("sphinx-multiversion"):
        subprocess.run(["sphinx-multiversion", SOURCE_DIR, os.path.join(BUILD_DIR, "html", "en")])
    else:
        Help.error("sphinx-multiversion not found! Pleas run \"pip install sphinx-multiversion\"")


@recipe(info="Clean build folder")
def clean():
    if os.path.exists(BUILD_DIR):
        Help.log("Cleaning folders..")
        shutil.rmtree(BUILD_DIR)


sane_run(default=html)
