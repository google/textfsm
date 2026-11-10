#!/usr/bin/env python3
#
# Copyright 2026 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Setup script."""

import re
# To use a consistent encoding
from codecs import open
from os import path
from pathlib import Path
from setuptools import find_packages, setup

here = Path(__file__).resolve().parent
init_py = (here / "textfsm" / "__init__.py").read_text(encoding="utf-8")
match = re.search(r'^__version__\s*=\s*[\'"]([^\'"]+)[\'"]', init_py, re.M)
if not match:
    raise RuntimeError("Unable to find __version__")
version = match.group(1)

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf8') as f:
    long_description = f.read()

setup(
    name='textfsm',
    maintainer='Google',
    maintainer_email='textfsm-dev@googlegroups.com',
    version=version,
    description=(
        'Python module for parsing semi-structured text into python tables.'
    ),
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/google/textfsm',
    license='Apache License, Version 2.0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries',
    ],
    packages=find_packages(),
    entry_points={'console_scripts': ['textfsm=textfsm.parser:main']},
    include_package_data=True,
    package_data={'textfsm': ['../testdata/*']},
)
