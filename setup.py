import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='krules-env',
    version="0.0.1",
    author="Alberto Degli Esposti",
    author_email="alberto@arispot.tech",
    description="KRules environment base package",
    license="Apache Licence 2.0",
    keywords="krules rules engine",
    url="...",  #TODO
    packages=find_packages(),
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: KRules",
        "License :: OSI Approved :: Apache Software License",
    ],
    install_requires=[
        # krules_cloudevents
        # krules_core
    ],
    setup_requires=[
        'pytest-runner',
    ],
    tests_require=[
        'pytest',
    ],
    # extras_require={
    #     'subject_redis': 'git+ssh://git@bitbucket.org/byters/krules-subject-redis.git#egg=krules-subject-redis-0.0.1'
    # }
)