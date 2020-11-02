import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='krules-env',
    version="0.5",
    author="Alberto Degli Esposti",
    author_email="alberto@arispot.tech",
    description="KRules environment base package",
    license="Apache Licence 2.0",
    keywords="krules rules engine",
    url="https://github.com/airspot-dev/krules-env",
    packages=find_packages(),
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: Apache Software License",
    ],
    install_requires=[
        "krules-dispatcher-cloudevents==0.5",
    ],
    setup_requires=[
        'pytest-runner',
    ],
    tests_require=[
        'pytest',
    ],
)
