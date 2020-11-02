import os

import setuptools
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='krules-dispatcher-cloudevents',
    version="0.5",
    author="Alberto Degli Esposti",
    author_email="alberto@arispot.tech",
    description="KRules cloudevents dispatcher",
    licence="Apache Licence 2.0",
    keywords="krules cloudevents router",
    url="https://github.com/airspot-dev/krules-dispatcher-cloudevents",
    packages=setuptools.find_packages(),
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: Apache Software License",
    ],
    install_requires=[
        'krules-core==0.5',
    ],
    setup_requires=[
        'pytest-runner',
    ],
    tests_require=[
        'pytest',
        'pytest-localserver',
    ],
)