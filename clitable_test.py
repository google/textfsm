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

"""Unittest for clitable script."""

import clitable
import copy
import copyable_regex_object
import cStringIO
import os
import re
import unittest


class UnitTestIndexTable(unittest.TestCase):
  """Tests the IndexTable class."""

  def testParseIndex(self):
    """Test reading and index and parsing to index and compiled tables."""
    file_path = os.path.join('testdata', 'parseindex_index')
    indx = clitable.IndexTable(file_path=file_path)
    # Compare number of entries found in the index table.
    self.failUnlessEqual(indx.index.size, 3)
    self.failUnlessEqual(indx.index[2]['Template'], 'clitable_templateC')
    self.failUnlessEqual(indx.index[3]['Template'], 'clitable_templateD')
    self.failUnlessEqual(indx.index[1]['Command'], 'sh[[ow]] ve[[rsion]]')
    self.failUnlessEqual(indx.index[1]['Hostname'], '.*')

    self.failUnlessEqual(indx.compiled.size, 3)
    for col in ('Command', 'Vendor', 'Template', 'Hostname'):
      self.failUnless(isinstance(indx.compiled[1][col],
                                 copyable_regex_object.CopyableRegexObject))

    self.failUnless(indx.compiled[1]['Hostname'].match('random string'))

    def _PreParse(key, value):
      if key == 'Template':
        return value.upper()
      return value

    def _PreCompile(key, value):
      if key in ('Template', 'Command'):
        return None
      return value

    self.failUnlessEqual(indx.compiled.size, 3)
    indx = clitable.IndexTable(_PreParse, _PreCompile, file_path)
    self.failUnlessEqual(indx.index[2]['Template'], 'CLITABLE_TEMPLATEC')
    self.failUnlessEqual(indx.index[1]['Command'], 'sh[[ow]] ve[[rsion]]')
    self.failUnless(isinstance(indx.compiled[1]['Hostname'],
                               copyable_regex_object.CopyableRegexObject))
    self.failIf(indx.compiled[1]['Command'])

  def testGetRowMatch(self):
    """Tests retreiving rows from table."""
    file_path = os.path.join('testdata', 'parseindex_index')
    indx = clitable.IndexTable(file_path=file_path)
    self.failUnlessEqual(1, indx.GetRowMatch({'Hostname': 'abc'}))
    self.failUnlessEqual(2, indx.GetRowMatch({'Hostname': 'abc',
                                              'Vendor': 'VendorB'}))

  def testCopy(self):
    """Tests copy of IndexTable object."""
    file_path = os.path.join('testdata', 'parseindex_index')
    indx = clitable.IndexTable(file_path=file_path)
    copy.deepcopy(indx)


class UnitTestCliTable(unittest.TestCase):
  """Tests the CliTable class."""

  def setUp(self):
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
    self.template_file = cStringIO.StringIO(self.template)

  def testCompletion(self):
    """Tests '[[]]' syntax replacement."""
    indx = clitable.CliTable()
    self.failUnlessEqual('abc',
                         re.sub('(\[\[.+?\]\])', indx._Completion, 'abc'))
    self.failUnlessEqual('a(b(c)?)?',
                         re.sub('(\[\[.+?\]\])', indx._Completion, 'a[[bc]]'))
    self.failUnlessEqual('a(b(c)?)? de(f)?',
                         re.sub('(\[\[.+?\]\])', indx._Completion,
                                'a[[bc]] de[[f]]'))

  def testRepeatRead(self):
    """Tests that index file is read only once at the class level."""
    new_clitable = clitable.CliTable('default_index', 'testdata')
    self.failUnlessEqual(self.clitable.index, new_clitable.index)

  def testCliCompile(self):
    """Tests PreParse and PreCompile."""

    self.failUnlessEqual('sh(o(w)?)? ve(r(s(i(o(n)?)?)?)?)?',
                         self.clitable.index.index[1]['Command'])
    self.failUnlessEqual(None, self.clitable.index.compiled[1]['Template'])
    self.failUnless(
        self.clitable.index.compiled[1]['Command'].match('sho vers'))

  def testParseCmdItem(self):
    """Tests parsing data with a single specific template."""
    t = self.clitable._ParseCmdItem(self.input_data,
                                    template_file=self.template_file)
    self.failUnlessEqual(t.table, 'Col1, Col2, Col3\na, b, c\nd, e, f\n')

  def testParseCmd(self):
    """Tests parsing data with a mocked template."""
    # Stub out the conversion of filename to file handle.
    self.clitable._TemplateNamesToFiles = lambda t: [self.template_file]
    self.clitable.ParseCmd(self.input_data, attributes={'Command': 'sh vers'})
    self.failUnlessEqual(
        self.clitable.table, 'Col1, Col2, Col3\na, b, c\nd, e, f\n')

  def testParseWithTemplate(self):
    """Tests parsing with an explicitly declared the template."""
    self.clitable.ParseCmd(self.input_data,
                           attributes={'Command': 'sh vers'},
                           templates='clitable_templateB')
    self.failUnlessEqual(
        self.clitable.table, 'Col1, Col4\na, b\nd, e\n')

  def testParseCmdFromIndex(self):
    """Tests parsing with a template found in the index."""
    self.clitable.ParseCmd(self.input_data,
                           attributes={'Command': 'sh vers',
                                       'Vendor': 'VendorB'})
    self.failUnlessEqual(
        self.clitable.table, 'Col1, Col2, Col3\na, b, c\n')
    self.clitable.ParseCmd(self.input_data,
                           attributes={'Command': 'sh int',
                                       'Vendor': 'VendorA'})
    self.failUnlessEqual(
        self.clitable.table, 'Col1, Col2, Col3\nd, e, f\n')

    self.failUnlessRaises(clitable.CliTableError, self.clitable.ParseCmd,
                          self.input_data,
                          attributes={'Command': 'show vers',
                                      'Vendor': 'bogus'})
    self.failUnlessRaises(clitable.CliTableError, self.clitable.ParseCmd,
                          self.input_data,
                          attributes={'Command': 'unknown command',
                                      'Vendor': 'VendorA'})

  def testParseWithMultiTemplates(self):
    """Tests that multiple matching templates extend the table."""
    self.clitable.ParseCmd(self.input_data,
                           attributes={'Command': 'sh ver',
                                       'Vendor': 'VendorA'})
    self.failUnlessEqual(
        self.clitable.table,
        'Col1, Col2, Col3, Col4\na, b, c, b\nd, e, f, e\n')
    self.clitable.ParseCmd(self.input_data,
                           attributes={'Command': 'sh vers'},
                           templates='clitable_templateB:clitable_templateA')
    self.failUnlessEqual(
        self.clitable.table,
        'Col1, Col4, Col2, Col3\na, b, b, c\nd, e, e, f\n')
    self.failUnlessRaises(IOError, self.clitable.ParseCmd,
                          self.input_data,
                          attributes={'Command': 'sh vers'},
                          templates='clitable_templateB:clitable_bogus')

  def testRequireCols(self):
    """Tests that CliTable expects a 'Template' row to be present."""
    self.failUnlessRaises(clitable.CliTableError, clitable.CliTable,
                          'nondefault_index', 'testdata')

  def testSuperKey(self):
    """Tests that superkey is derived from the template and is extensible."""
    # Stub out the conversion of filename to file handle.
    self.clitable._TemplateNamesToFiles = lambda t: [self.template_file]
    self.clitable.ParseCmd(self.input_data, attributes={'Command': 'sh ver'})
    self.failUnlessEqual(self.clitable.superkey, ['Col1'])
    self.failUnlessEqual(
        self.clitable.LabelValueTable(),
        '# LABEL Col1\n'
        'a.Col2 b\n'
        'a.Col3 c\n'
        'd.Col2 e\n'
        'd.Col3 f\n')

    self.clitable.AddKeys(['Col2'])
    self.failUnlessEqual(
        self.clitable.LabelValueTable(),
        '# LABEL Col1.Col2\n'
        'a.b.Col3 c\n'
        'd.e.Col3 f\n')

  def testAddKey(self):
    """Tests that new keys are not duplicated and non-existant columns."""
    self.failUnlessEqual(self.clitable.superkey, [])
    # Stub out the conversion of filename to file handle.
    self.clitable._TemplateNamesToFiles = lambda t: [self.template_file]
    self.clitable.ParseCmd(self.input_data, attributes={'Command': 'sh ver'})
    self.failUnlessEqual(self.clitable.superkey, ['Col1'])
    self.clitable.AddKeys(['Col1', 'Col2', 'Col3'])
    self.failUnlessEqual(self.clitable.superkey, ['Col1', 'Col2', 'Col3'])
    self.failUnlessRaises(KeyError, self.clitable.AddKeys, ['Bogus'])

  def testKeyValue(self):
    """Tests retrieving row value that corresponds to the key."""
    # Stub out the conversion of filename to file handle.
    self.clitable._TemplateNamesToFiles = lambda t: [self.template_file]
    self.clitable.ParseCmd(self.input_data, attributes={'Command': 'sh ver'})
    self.failUnlessEqual(self.clitable.KeyValue(), ['a'])
    self.clitable.row_index = 2
    self.failUnlessEqual(self.clitable.KeyValue(), ['d'])
    self.clitable.row_index = 1
    self.clitable.AddKeys(['Col3'])
    self.failUnlessEqual(self.clitable.KeyValue(), ['a', 'c'])
    # With no key it falls back to row number.
    self.clitable._keys = set()
    for rownum, row in enumerate(self.clitable, start=1):
      self.failUnlessEqual(row.table.KeyValue(), ['%s' % rownum])

  def testTableSort(self):
    """Tests sorting of table based on superkey."""
    self.clitable._TemplateNamesToFiles = lambda t: [self.template_file]
    input_data2 = ('a e c\n'
                   'd b f\n')
    self.clitable.ParseCmd(self.input_data + input_data2,
                           attributes={'Command': 'sh ver'})
    self.failUnlessEqual(
        self.clitable.table,
        'Col1, Col2, Col3\na, b, c\nd, e, f\na, e, c\nd, b, f\n')
    self.clitable.sort()
    # Key was non-unique, columns outside of the key do not count.
    self.failUnlessEqual(
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
    self.template_file = cStringIO.StringIO(self.template)
    self.clitable._TemplateNamesToFiles = lambda t: [self.template_file]
    self.clitable.ParseCmd(self.input_data + input_data2,
                           attributes={'Command': 'sh ver'})
    # Add a manual key.
    self.clitable.AddKeys(['Col2'])
    self.clitable.sort()
    self.failUnlessEqual(
        self.clitable.table,
        'Col1, Col2, Col3\na, b, c\nd, b, f\nd, e, f\na, e, c\n')
    # Clear the keys.
    self.clitable._keys = set()
    # With no key, sort based on whole row.
    self.clitable.sort()
    self.failUnlessEqual(
        self.clitable.table,
        'Col1, Col2, Col3\na, b, c\na, e, c\nd, b, f\nd, e, f\n')

  def testCopy(self):
    """Tests copying of clitable object."""
    copy.deepcopy(self.clitable)


if __name__ == '__main__':
  unittest.main()
