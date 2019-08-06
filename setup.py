import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='krules-python-core',
    version="0.0.1",
    author="Alberto Degli Esposti",
    author_email="alberto@arisport.tech",
    description="KRules Python core package",
    licence="Apache Licence 2.0",
    keywords="krules rules engine",
    url="...",  #TODO
    packages=find_packages(), #['krules_core'],
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: KRules",
        "License :: OSI Approved :: Apache Software License",
    ],
    install_requires=[
        'dependency-injector>=3.14.8',
        'rx==1.6.1',
        'wrapt>=1.11.2',
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