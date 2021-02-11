import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='krules-flask-env',
    version="0.8.2",
    author="Alberto Degli Esposti",
    author_email="alberto@arispot.tech",
    description="KRules environment base package",
    license="Apache Licence 2.0",
    keywords="krules rules engine flask",
    url="https://github.com/airspot-dev/krules-flask-env",
    packages=find_packages(),
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: Apache Software License",
    ],
    install_requires=[
        "krules-env==0.8.2",
        "flask==1.1.2",
        "json-logging==1.2.11"
    ],
    setup_requires=[
        'pytest-runner',
    ],
    tests_require=[
        'pytest',
    ],
)
