import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='krules-core',
    version="0.5",
    author="Alberto Degli Esposti",
    author_email="alberto@arispot.tech",
    description="KRules Python core package",
    license="Apache Licence 2.0",
    keywords="krules rules engine",
    url="https://github.com/airspot-dev/krules-core",
    packages=find_packages(),
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: Apache Software License",
    ],
    python_requires='>3.7',
    install_requires=[
        'dependency-injector>=3.14.8',
        'rx==1.6.1',
        'wrapt>=1.11.2',
        'jsonpatch==1.26',
        'jsonpath-rw-ext==1.2.2',
    ],
    setup_requires=[
        'pytest-runner',
    ],
    tests_require=[
        'pytest',
    ],
)