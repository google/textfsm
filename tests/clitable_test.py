#!/usr/bin/python
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

"""Unittest for clitable script."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import copy
import os
import re
import unittest

from io import StringIO
from textfsm import clitable
from textfsm import copyable_regex_object


class UnitTestIndexTable(unittest.TestCase):
  """Tests the IndexTable class."""

  def testParseIndex(self):
    """Test reading and index and parsing to index and compiled tables."""
    file_path = os.path.join('testdata', 'parseindex_index')
    indx = clitable.IndexTable(file_path=file_path)
    # Compare number of entries found in the index table.
    self.assertEqual(indx.index.size, 3)
    self.assertEqual(indx.index[2]['Template'], 'clitable_templateC')
    self.assertEqual(indx.index[3]['Template'], 'clitable_templateD')
    self.assertEqual(indx.index[1]['Command'], 'sh[[ow]] ve[[rsion]]')
    self.assertEqual(indx.index[1]['Hostname'], '.*')

    self.assertEqual(indx.compiled.size, 3)
    for col in ('Command', 'Vendor', 'Template', 'Hostname'):
      self.assertTrue(isinstance(indx.compiled[1][col],
                                 copyable_regex_object.CopyableRegexObject))

    self.assertTrue(indx.compiled[1]['Hostname'].match('random string'))

    def _PreParse(key, value):
      if key == 'Template':
        return value.upper()
      return value

    def _PreCompile(key, value):
      if key in ('Template', 'Command'):
        return None
      return value

    self.assertEqual(indx.compiled.size, 3)
    indx = clitable.IndexTable(_PreParse, _PreCompile, file_path)
    self.assertEqual(indx.index[2]['Template'], 'CLITABLE_TEMPLATEC')
    self.assertEqual(indx.index[1]['Command'], 'sh[[ow]] ve[[rsion]]')
    self.assertTrue(isinstance(indx.compiled[1]['Hostname'],
                               copyable_regex_object.CopyableRegexObject))
    self.assertFalse(indx.compiled[1]['Command'])

  def testGetRowMatch(self):
    """Tests retreiving rows from table."""
    file_path = os.path.join('testdata', 'parseindex_index')
    indx = clitable.IndexTable(file_path=file_path)
    self.assertEqual(1, indx.GetRowMatch({'Hostname': 'abc'}))
    self.assertEqual(2, indx.GetRowMatch({'Hostname': 'abc',
                                          'Vendor': 'VendorB'}))

  def testCopy(self):
    """Tests copy of IndexTable object."""
    file_path = os.path.join('testdata', 'parseindex_index')
    indx = clitable.IndexTable(file_path=file_path)
    copy.deepcopy(indx)


class UnitTestCliTable(unittest.TestCase):
  """Tests the CliTable class."""

  def setUp(self):
    super(UnitTestCliTable, self).setUp()
    clitable.CliTable.INDEX = {}
    self.clitable = clitable.CliTable('default_index', 'testdata')
    self.input_data = ('a b c\n'
                       'd e f\n')
    self.template = ('Value Key Col1 (.)\n'
                     'Value Col2 (.)\n'
                     'Value Col3 (.)\n'
                     '\n'
                     'Start\n'
                     '  ^${Col1} ${Col2} ${Col3} -> Record\n'
                     '\n')
    self.template_file = StringIO(self.template)

  def testCompletion(self):
    """Tests '[[]]' syntax replacement."""
    indx = clitable.CliTable()
    self.assertEqual('abc', re.sub(r'(\[\[.+?\]\])', indx._Completion, 'abc'))
    self.assertEqual('a(b(c)?)?',
                     re.sub(r'(\[\[.+?\]\])', indx._Completion, 'a[[bc]]'))
    self.assertEqual('a(b(c)?)? de(f)?',
                     re.sub(r'(\[\[.+?\]\])', indx._Completion,
                            'a[[bc]] de[[f]]'))

  def testRepeatRead(self):
    """Tests that index file is read only once at the class level."""
    new_clitable = clitable.CliTable('default_index', 'testdata')
    self.assertEqual(self.clitable.index, new_clitable.index)

  def testCliCompile(self):
    """Tests PreParse and PreCompile."""

    self.assertEqual('sh(o(w)?)? ve(r(s(i(o(n)?)?)?)?)?',
                     self.clitable.index.index[1]['Command'])
    self.assertEqual(None, self.clitable.index.compiled[1]['Template'])
    self.assertTrue(
        self.clitable.index.compiled[1]['Command'].match('sho vers'))

  def testParseCmdItem(self):
    """Tests parsing data with a single specific template."""
    t = self.clitable._ParseCmdItem(self.input_data,
                                    template_file=self.template_file)
    self.assertEqual(t.table, 'Col1, Col2, Col3\na, b, c\nd, e, f\n')

  def testParseCmd(self):
    """Tests parsing data with a mocked template."""
    # Stub out the conversion of filename to file handle.
    self.clitable._TemplateNamesToFiles = lambda t: [self.template_file]
    self.clitable.ParseCmd(self.input_data, attributes={'Command': 'sh vers'})
    self.assertEqual(
        self.clitable.table, 'Col1, Col2, Col3\na, b, c\nd, e, f\n')

  def testParseWithTemplate(self):
    """Tests parsing with an explicitly declared the template."""
    self.clitable.ParseCmd(self.input_data,
                           attributes={'Command': 'sh vers'},
                           templates='clitable_templateB')
    self.assertEqual(
        self.clitable.table, 'Col1, Col4\na, b\nd, e\n')

  def testParseCmdFromIndex(self):
    """Tests parsing with a template found in the index."""
    self.clitable.ParseCmd(self.input_data,
                           attributes={'Command': 'sh vers',
                                       'Vendor': 'VendorB'})
    self.assertEqual(
        self.clitable.table, 'Col1, Col2, Col3\na, b, c\n')
    self.clitable.ParseCmd(self.input_data,
                           attributes={'Command': 'sh int',
                                       'Vendor': 'VendorA'})
    self.assertEqual(
        self.clitable.table, 'Col1, Col2, Col3\nd, e, f\n')

    self.assertRaises(clitable.CliTableError, self.clitable.ParseCmd,
                      self.input_data,
                      attributes={'Command': 'show vers',
                                  'Vendor': 'bogus'})
    self.assertRaises(clitable.CliTableError, self.clitable.ParseCmd,
                      self.input_data,
                      attributes={'Command': 'unknown command',
                                  'Vendor': 'VendorA'})

  def testParseWithMultiTemplates(self):
    """Tests that multiple matching templates extend the table."""
    self.clitable.ParseCmd(self.input_data,
                           attributes={'Command': 'sh ver',
                                       'Vendor': 'VendorA'})
    self.assertEqual(
        self.clitable.table,
        'Col1, Col2, Col3, Col4\na, b, c, b\nd, e, f, e\n')
    self.clitable.ParseCmd(self.input_data,
                           attributes={'Command': 'sh vers'},
                           templates='clitable_templateB:clitable_templateA')
    self.assertEqual(
        self.clitable.table,
        'Col1, Col4, Col2, Col3\na, b, b, c\nd, e, e, f\n')
    self.assertRaises(IOError, self.clitable.ParseCmd,
                      self.input_data,
                      attributes={'Command': 'sh vers'},
                      templates='clitable_templateB:clitable_bogus')

  def testRequireCols(self):
    """Tests that CliTable expects a 'Template' row to be present."""
    self.assertRaises(clitable.CliTableError, clitable.CliTable,
                      'nondefault_index', 'testdata')

  def testSuperKey(self):
    """Tests that superkey is derived from the template and is extensible."""
    # Stub out the conversion of filename to file handle.
    self.clitable._TemplateNamesToFiles = lambda t: [self.template_file]
    self.clitable.ParseCmd(self.input_data, attributes={'Command': 'sh ver'})
    self.assertEqual(self.clitable.superkey, ['Col1'])
    self.assertEqual(
        self.clitable.LabelValueTable(),
        '# LABEL Col1\n'
        'a.Col2 b\n'
        'a.Col3 c\n'
        'd.Col2 e\n'
        'd.Col3 f\n')

    self.clitable.AddKeys(['Col2'])
    self.assertEqual(
        self.clitable.LabelValueTable(),
        '# LABEL Col1.Col2\n'
        'a.b.Col3 c\n'
        'd.e.Col3 f\n')

  def testAddKey(self):
    """Tests that new keys are not duplicated and non-existant columns."""
    self.assertEqual(self.clitable.superkey, [])
    # Stub out the conversion of filename to file handle.
    self.clitable._TemplateNamesToFiles = lambda t: [self.template_file]
    self.clitable.ParseCmd(self.input_data, attributes={'Command': 'sh ver'})
    self.assertEqual(self.clitable.superkey, ['Col1'])
    self.clitable.AddKeys(['Col1', 'Col2', 'Col3'])
    self.assertEqual(self.clitable.superkey, ['Col1', 'Col2', 'Col3'])
    self.assertRaises(KeyError, self.clitable.AddKeys, ['Bogus'])

  def testKeyValue(self):
    """Tests retrieving row value that corresponds to the key."""
    # Stub out the conversion of filename to file handle.
    self.clitable._TemplateNamesToFiles = lambda t: [self.template_file]
    self.clitable.ParseCmd(self.input_data, attributes={'Command': 'sh ver'})
    self.assertEqual(self.clitable.KeyValue(), ['a'])
    self.clitable.row_index = 2
    self.assertEqual(self.clitable.KeyValue(), ['d'])
    self.clitable.row_index = 1
    self.clitable.AddKeys(['Col3'])
    self.assertEqual(self.clitable.KeyValue(), ['a', 'c'])
    # With no key it falls back to row number.
    self.clitable._keys = set()
    for rownum, row in enumerate(self.clitable, start=1):
      self.assertEqual(row.table.KeyValue(), ['%s' % rownum])

  def testTableSort(self):
    """Tests sorting of table based on superkey."""
    self.clitable._TemplateNamesToFiles = lambda t: [self.template_file]
    input_data2 = ('a e c\n'
                   'd b f\n')
    self.clitable.ParseCmd(self.input_data + input_data2,
                           attributes={'Command': 'sh ver'})
    self.assertEqual(
        self.clitable.table,
        'Col1, Col2, Col3\na, b, c\nd, e, f\na, e, c\nd, b, f\n')
    self.clitable.sort()
    # Key was non-unique, columns outside of the key do not count.
    self.assertEqual(
        self.clitable.table,
        'Col1, Col2, Col3\na, b, c\na, e, c\nd, e, f\nd, b, f\n')

    # Create a new table with no explicit key.
    self.template = ('Value Col1 (.)\n'
                     'Value Col2 (.)\n'
                     'Value Col3 (.)\n'
                     '\n'
                     'Start\n'
                     '  ^${Col1} ${Col2} ${Col3} -> Record\n'
                     '\n')
    self.template_file = StringIO(self.template)
    self.clitable._TemplateNamesToFiles = lambda t: [self.template_file]
    self.clitable.ParseCmd(self.input_data + input_data2,
                           attributes={'Command': 'sh ver'})
    # Add a manual key.
    self.clitable.AddKeys(['Col2'])
    self.clitable.sort()
    self.assertEqual(
        self.clitable.table,
        'Col1, Col2, Col3\na, b, c\nd, b, f\nd, e, f\na, e, c\n')
    # Clear the keys.
    self.clitable._keys = set()
    # With no key, sort based on whole row.
    self.clitable.sort()
    self.assertEqual(
        self.clitable.table,
        'Col1, Col2, Col3\na, b, c\na, e, c\nd, b, f\nd, e, f\n')

  def testCopy(self):
    """Tests copying of clitable object."""
    copy.deepcopy(self.clitable)


if __name__ == '__main__':
  unittest.main()
