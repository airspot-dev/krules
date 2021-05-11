import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='krules-dev',
    version="0.8.5.1",
    author="Alberto Degli Esposti",
    author_email="alberto@arispot.tech",
    description="KRules dev utilities",
    license="Apache Licence 2.0",
    keywords="krules rules engine sane-build",
    url="https://github.com/airspot-dev/krules",
    packages=find_packages(),
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: Apache Software License",
    ],
    python_requires='>3.7',
    install_requires=[
        'jinja2==2.11.3',
        'sane-build==7.1',
    ],
    setup_requires=[
        'pytest-runner',
    ],
    tests_require=[
        'pytest',
    ],
)
