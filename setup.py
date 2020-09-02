# Copyright 2019 The KRules Authors
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='krules-subjects-storage-redis',
    version="0.4.1",
    author="Alberto Degli Esposti",
    author_email="alberto@arispot.tech",
    description="KRules redis subjects storage implementation",
    licence="Apache Licence 2.0",
    keywords="krules subject redis",
    url="https://github.com/airspot-dev/krules-subjects-redis-storage.git",
    packages=find_packages(),
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: Apache Software License",
    ],
    install_requires=[
        'redis>=3.3.5',
        'anyjson>=0.3.3',
        'krules-core==0.4.1',
    ],
    setup_requires=[
        'pytest-runner',
    ],
    tests_require=[
        'pytest',
    ],
)