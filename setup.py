#!/usr/bin/python
#
# Copyright 2010 Google Inc.
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

from distutils.core import setup

import textfsm


setup(name='textfsm',
      maintainer='Google',
      maintainer_email='textfsm-dev@googlegroups.com',
      version=textfsm.__version__,
      url='https://code.google.com/p/textfsm/',
      license='Apache License, Version 2.0',
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: Apache Software License',
          'Operating System :: OS Independent',
          'Topic :: Software Development :: Libraries'],
      requires=['terminal'],
      py_modules=['clitable', 'textfsm', 'copyable_regex_object', 'texttable'])
