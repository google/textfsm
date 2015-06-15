#!/usr/bin/python2.6
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.

"""Tests for copyable_regex_object."""

import copy
import copyable_regex_object
import unittest


class CopyableRegexObjectTest(unittest.TestCase):

  def testCopyableRegexObject(self):
    obj1 = copyable_regex_object.CopyableRegexObject('fo*')
    self.assertTrue(obj1.match('foooo'))
    self.assertFalse(obj1.match('bar'))
    obj2 = copy.copy(obj1)
    self.assertTrue(obj2.match('foooo'))
    self.assertFalse(obj2.match('bar'))


if __name__ == '__main__':
  unittest.main()
