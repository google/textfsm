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

"""Unittest for text table."""

import StringIO
import unittest
import terminal
import texttable


class UnitTestRow(unittest.TestCase):
  """Tests texttable.Row() class."""

  def setUp(self):
    self.row = texttable.Row()
    self.row._keys = ['a', 'b', 'c']
    self.row._values = ['1', '2', '3']

  def testRowBasicMethods(self):
    row = texttable.Row()
    # Setting columns (__setitem__).
    row['a'] = 'one'
    row['b'] = 'two'
    row['c'] = 'three'

    # Access a single column (__getitem__).
    self.failUnlessEqual('one', row['a'])
    self.failUnlessEqual('two', row['b'])
    self.failUnlessEqual('three', row['c'])

    # Access multiple columns (__getitem__).
    self.failUnlessEqual(['one', 'three'], row[('a', 'c')])
    self.failUnlessEqual(['two', 'three'], row[('b', 'c')])

    # Access integer indexes (__getitem__).
    self.failUnlessEqual('one', row[0])
    self.failUnlessEqual(['two', 'three'], row[1:])

    # Change existing column value.
    row['b'] = 'Two'
    self.failUnlessEqual('Two', row['b'])

    # Length.
    self.failUnlessEqual(3, len(row))

    # Contains.
    self.failUnless(not 'two' in row)
    self.failUnless('Two' in row)

    # Iteration.
    self.failUnlessEqual(['one', 'Two', 'three'], list(row))

  def testRowPublicMethods(self):
    self.row.header = ('x', 'y', 'z')
    # Header should be set, values initialised to None.
    self.failUnlessEqual(['x', 'y', 'z'], self.row.header)
    self.failUnlessEqual(['1', '2', '3'], self.row.values)
    row = texttable.Row()
    row.header = ('x', 'y', 'z')
    self.failUnlessEqual(['x', 'y', 'z'], row.header)
    self.failUnlessEqual([None, None, None], row.values)

  def testSetValues(self):
    """Tests setting row values from 'From' method."""

    # Set values from Dict.
    self.row._SetValues({'a': 'seven', 'b': 'eight', 'c': 'nine'})
    self.failUnlessEqual(['seven', 'eight', 'nine'], self.row._values)
    self.row._SetValues({'b': '8', 'a': '7', 'c': '9'})
    self.failUnlessEqual(['7', '8', '9'], self.row._values)

    # Converts integers to string equivalents.
    # Excess key/value pairs are ignored.
    self.row._SetValues({'a': 1, 'b': 2, 'c': 3, 'd': 4})
    self.failUnlessEqual(['1', '2', '3'], self.row._values)

    # Values can come from a list of equal length the the keys.
    self.row._SetValues((7, '8', 9))
    self.failUnlessEqual(['7', '8', '9'], self.row._values)

    # Or from a tuple of the same length.
    self.row._SetValues(('vb', 'coopers', 'squires'))
    self.failUnlessEqual(['vb', 'coopers', 'squires'], self.row._values)

    # Raise error if list length is incorrect.
    self.failUnlessRaises(TypeError, self.row._SetValues,
                          ['seven', 'eight', 'nine', 'ten'])
    # Raise error if row object has mismatched header.
    row = texttable.Row()
    self.row._keys = ['a']
    self.row._values = ['1']
    self.failUnlessRaises(TypeError, self.row._SetValues, row)
    # Raise error if assigning wrong data type.
    self.failUnlessRaises(TypeError, row._SetValues, 'abc')

  def testHeader(self):
    """Tests value property."""
    self.row.header = ('x', 'y', 'z')
    self.failUnlessEqual(['x', 'y', 'z'], self.row.header)
    self.failUnlessRaises(ValueError, self.row._SetHeader, ('a', 'b', 'c', 'd'))

  def testValue(self):
    """Tests value property."""
    self.row.values = {'a': 'seven', 'b': 'eight', 'c': 'nine'}
    self.failUnlessEqual(['seven', 'eight', 'nine'], self.row.values)
    self.row.values = (7, '8', 9)
    self.failUnlessEqual(['7', '8', '9'], self.row.values)

  def testIndex(self):
    """Tests Insert and Index methods."""

    self.failUnlessEqual(1, self.row.index('b'))
    self.failUnlessRaises(ValueError, self.row.index, 'bogus')

    # Insert element within row.
    self.row.Insert('black', 'white', 1)
    self.row.Insert('red', 'yellow', -1)
    self.failUnlessEqual(['a', 'black', 'b', 'red', 'c'], self.row.header)
    self.failUnlessEqual(['1', 'white', '2', 'yellow', '3'], self.row.values)
    self.failUnlessEqual(1, self.row.index('black'))
    self.failUnlessEqual(2, self.row.index('b'))
    self.failUnlessRaises(IndexError, self.row.Insert, 'grey', 'gray', 6)
    self.failUnlessRaises(IndexError, self.row.Insert, 'grey', 'gray', -7)


class MyRow(texttable.Row):
  pass


class UnitTestTextTable(unittest.TestCase):

  def _BasicTable(self):
    t = texttable.TextTable()
    t.header = ('a', 'b', 'c')
    t.Append(('1', '2', '3'))
    t.Append(('10', '20', '30'))
    return t

  def testCustomRow(self):
    table = texttable.TextTable()
    table.header = ('a', 'b', 'c')
    self.failUnlessEqual(type(texttable.Row()), type(table[0]))
    table = texttable.TextTable(row_class=MyRow)
    self.failUnlessEqual(MyRow, table.row_class)
    table.header = ('a', 'b', 'c')
    self.failUnlessEqual(type(MyRow()), type(table[0]))

  def testTableRepr(self):
    self.failUnlessEqual(
        "TextTable('a, b, c\\n1, 2, 3\\n10, 20, 30\\n')",
        repr(self._BasicTable()))

  def testTableStr(self):
    self.failUnlessEqual('a, b, c\n1, 2, 3\n10, 20, 30\n',
                         self._BasicTable().__str__())

  def testTableSetRow(self):
    t = self._BasicTable()
    t.Append(('one', 'two', 'three'))
    self.failUnlessEqual(['one', 'two', 'three'], t[3].values)
    self.failUnlessEqual(3, t.size)

  def testTableRowTypes(self):
    t = self._BasicTable()
    t.Append(('one', ['two', None], None))
    self.failUnlessEqual(['one', ['two', 'None'], 'None'], t[3].values)
    self.failUnlessEqual(3, t.size)

  def testTableRowDictWithInt(self):
    t = self._BasicTable()
    t.Append({'a': 1, 'b': 'two', 'c': 3})
    self.failUnlessEqual(['1', 'two', '3'], t[3].values)
    self.failUnlessEqual(3, t.size)

  def testTableRowListWithInt(self):
    t = self._BasicTable()
    t.Append([1, 'two', 3])
    self.failUnlessEqual(['1', 'two', '3'], t[3].values)
    self.failUnlessEqual(3, t.size)

  def testTableGetRow(self):
    t = self._BasicTable()
    self.failUnlessEqual(['1', '2', '3'], t[1].values)
    self.failUnlessEqual(['1', '3'], t[1][('a', 'c')])
    self.failUnlessEqual('3', t[1][('c')])
    for rnum in xrange(t.size):
      self.failUnlessEqual(rnum, t[rnum].row)

  def testTableRowWith(self):
    t = self._BasicTable()
    self.failUnlessEqual(t.RowWith('a', '10'), t[2])
    self.failUnlessRaises(IndexError, t.RowWith, 'g', '5')

  def testContains(self):
    t = self._BasicTable()
    self.failUnless('a' in t)
    self.failIf('x' in t)

  def testIteration(self):
    t = self._BasicTable()
    index = 0
    for r in t:
      index += 1
      self.failUnlessEqual(r, t[index])
      self.failUnlessEqual(index, r.table._iterator)

    # Have we iterated over all entries.
    self.failUnlessEqual(index, t.size)
    # The iterator count is reset.
    self.failUnlessEqual(0, t._iterator)

    # Can we iterate repeatedly.
    index = 0
    for r in t:
      index += 1
      self.failUnlessEqual(r, t[index])

    index1 = 0
    try:
      for r in t:
        index1 += 1
        index2 = 0
        self.failUnlessEqual(index1, r.table._iterator)
        # Test nesting of iterations.
        for r2 in t:
          index2 += 1
          self.failUnlessEqual(index2, r2.table._iterator)
          # Preservation of outer iterator after 'break'.
          if index1 == 2 and index2 == 2:
            break
        if index1 == 2:
          # Restoration of initial iterator after exception.
          raise IndexError
        self.failUnlessEqual(index1, r.table._iterator)
    except IndexError:
      pass

    # Have we iterated over all entries - twice.
    self.failUnlessEqual(index, t.size)
    self.failUnlessEqual(index2, t.size)
    # The iterator count is reset.
    self.failUnlessEqual(0, t._iterator)

  def testCsvToTable(self):
    buf = """
    # A comment
a,b, c, d  # Trim comment
# Inline comment
# 1,2,3,4
1,2,3,4
5, 6, 7, 8
10, 11
# More comments.
"""
    f = StringIO.StringIO(buf)
    t = texttable.TextTable()
    self.failUnlessEqual(2, t.CsvToTable(f))
    # pylint: disable-msg=E1101
    self.failUnlessEqual(['a', 'b', 'c', 'd'], t.header.values)
    self.failUnlessEqual(['1', '2', '3', '4'], t[1].values)
    self.failUnlessEqual(['5', '6', '7', '8'], t[2].values)
    self.failUnlessEqual(2, t.size)

  def testHeaderIndex(self):
    t = self._BasicTable()
    self.failUnlessEqual('c', t.header[2])
    self.failUnlessEqual('a', t.header[0])

  def testAppend(self):
    t = self._BasicTable()
    t.Append(['10', '20', '30'])
    self.failUnlessEqual(3, t.size)
    self.failUnlessEqual(['10', '20', '30'], t[3].values)

    t.Append(('100', '200', '300'))
    self.failUnlessEqual(4, t.size)
    self.failUnlessEqual(['100', '200', '300'], t[4].values)

    t.Append(t[1])
    self.failUnlessEqual(5, t.size)
    self.failUnlessEqual(['1', '2', '3'], t[5].values)

    t.Append({'a': '11', 'b': '12', 'c': '13'})
    self.failUnlessEqual(6, t.size)
    self.failUnlessEqual(['11', '12', '13'], t[6].values)

    # The row index and container table should be set on new rows.
    self.failUnlessEqual(6, t[6].row)
    self.failUnlessEqual(t[1].table, t[6].table)

    self.failUnlessRaises(TypeError, t.Append, ['20', '30'])
    self.failUnlessRaises(TypeError, t.Append, ('1', '2', '3', '4'))
    self.failUnlessRaises(TypeError, t.Append,
                          {'a': '11', 'b': '12', 'd': '13'})

  def testDeleteRow(self):
    t = self._BasicTable()
    self.failUnlessEqual(2, t.size)
    t.Remove(1)
    self.failUnlessEqual(['10', '20', '30'], t[1].values)
    for row in t:
      self.failUnlessEqual(row, t[row.row])
    t.Remove(1)
    self.failIf(t.size)

  def testRowNumberandParent(self):
    t = self._BasicTable()
    t.Append(['10', '20', '30'])
    t.Remove(1)
    for rownum, row in enumerate(t, start=1):
      self.failUnlessEqual(row.row, rownum)
      self.failUnlessEqual(row.table, t)
    t2 = self._BasicTable()
    t.table = t2
    for rownum, row in enumerate(t, start=1):
      self.failUnlessEqual(row.row, rownum)
      self.failUnlessEqual(row.table, t)

  def testAddColumn(self):
    t = self._BasicTable()
    t.AddColumn('Beer')
    # pylint: disable-msg=E1101
    self.failUnlessEqual(['a', 'b', 'c', 'Beer'], t.header.values)
    self.failUnlessEqual(['10', '20', '30', ''], t[2].values)

    t.AddColumn('Wine', default='Merlot', col_index=1)
    self.failUnlessEqual(['a', 'Wine', 'b', 'c', 'Beer'], t.header.values)
    self.failUnlessEqual(['10', 'Merlot', '20', '30', ''], t[2].values)

    t.AddColumn('Spirits', col_index=-2)
    self.failUnlessEqual(['a', 'Wine', 'b', 'Spirits', 'c', 'Beer'],
                         t.header.values)
    self.failUnlessEqual(['10', 'Merlot', '20', '', '30', ''], t[2].values)

    self.failUnlessRaises(IndexError, t.AddColumn, 'x', col_index=6)
    self.failUnlessRaises(IndexError, t.AddColumn, 'x', col_index=-7)
    self.failUnlessRaises(texttable.TableError, t.AddColumn, 'b')

  def testAddTable(self):
    t = self._BasicTable()
    t2 = self._BasicTable()
    t3 = t + t2
    # pylint: disable-msg=E1101
    self.failUnlessEqual(['a', 'b', 'c'], t3.header.values)
    self.failUnlessEqual(['10', '20', '30'], t3[2].values)
    self.failUnlessEqual(['10', '20', '30'], t3[4].values)
    self.failUnlessEqual(4, t3.size)

  def testExtendTable(self):
    t2 = self._BasicTable()
    t2.AddColumn('Beer')
    t2[1]['Beer'] = 'Lager'
    t2[1]['three'] = 'three'
    t2.Append(('one', 'two', 'three', 'Stout'))

    t = self._BasicTable()
    # Explicit key, use first column.
    t.extend(t2, ('a',))
    # pylint: disable-msg=E1101
    self.failUnlessEqual(['a', 'b', 'c', 'Beer'], t.header.values)
    # Only new columns have updated values.
    self.failUnlessEqual(['1', '2', '3', 'Lager'], t[1].values)
    # All rows are extended.
    self.failUnlessEqual(['10', '20', '30', ''], t[2].values)
    # The third row of 't2', is not included as there is no matching
    # row with the same key in the first table 't'.
    self.failUnlessEqual(2, t.size)

    # pylint: disable-msg=E1101
    t = self._BasicTable()
    # If a Key is non-unique (which is a soft-error), then the first instance
    # on the RHS is used for and applied to all non-unique entries on the LHS.
    t.Append(('1', '2b', '3b'))
    t2.Append(('1', 'two', '', 'Ale'))
    t.extend(t2, ('a',))
    self.failUnlessEqual(['1', '2', '3', 'Lager'], t[1].values)
    self.failUnlessEqual(['1', '2b', '3b', 'Lager'], t[3].values)

    t = self._BasicTable()
    # No explicit key, row number is used as the key.
    t.extend(t2)
    self.failUnlessEqual(['a', 'b', 'c', 'Beer'], t.header.values)
    # Since row is key we pick up new values from corresponding row number.
    self.failUnlessEqual(['1', '2', '3', 'Lager'], t[1].values)
    # All rows are still extended.
    self.failUnlessEqual(['10', '20', '30', ''], t[2].values)
    # The third/fourth row of 't2', is not included as there is no corresponding
    # row in the first table 't'.
    self.failUnlessEqual(2, t.size)

    t = self._BasicTable()
    t.Append(('1', 'two', '3'))
    t.Append(('two', '1', 'three'))
    t2 = texttable.TextTable()
    t2.header = ('a', 'b', 'c', 'Beer')
    t2.Append(('1', 'two', 'three', 'Stout'))
    # Explicitly declare which columns constitute the key.
    # Sometimes more than one row is needed to define a unique key (superkey).
    t.extend(t2, ('a', 'b'))

    self.failUnlessEqual(['a', 'b', 'c', 'Beer'], t.header.values)
    # key '1', '2' does not equal '1', 'two', so column unmatched.
    self.failUnlessEqual(['1', '2', '3', ''], t[1].values)
    # '1', 'two' matches but 'two', '1' does not as order is important.
    self.failUnlessEqual(['1', 'two', '3', 'Stout'], t[3].values)
    self.failUnlessEqual(['two', '1', 'three', ''], t[4].values)
    self.failUnlessEqual(4, t.size)

    # Expects a texttable as the argument.
    self.failUnlessRaises(AttributeError, t.extend, ['a', 'list'])
    # All Key column Names must be valid.
    self.failUnlessRaises(IndexError, t.extend, ['a', 'list'], ('a', 'bogus'))

  def testTableWithLabels(self):
    t = self._BasicTable()
    self.failUnlessEqual(
        '# LABEL a\n1.b 2\n1.c 3\n10.b 20\n10.c 30\n',
        t.LabelValueTable())
    self.failUnlessEqual(
        '# LABEL a\n1.b 2\n1.c 3\n10.b 20\n10.c 30\n',
        t.LabelValueTable(['a']))
    self.failUnlessEqual(
        '# LABEL a.c\n1.3.b 2\n10.30.b 20\n',
        t.LabelValueTable(['a', 'c']))
    self.failUnlessEqual(
        '# LABEL a.c\n1.3.b 2\n10.30.b 20\n',
        t.LabelValueTable(['c', 'a']))
    self.failUnlessRaises(texttable.TableError, t.LabelValueTable, ['a', 'z'])

  def testTextJustify(self):
    t = texttable.TextTable()
    self.failUnlessEqual([' a    '], t._TextJustify('a', 6))
    self.failUnlessEqual([' a b  '], t._TextJustify('a b', 6))
    self.failUnlessEqual([' a  b '], t._TextJustify('a  b', 6))
    self.failUnlessEqual([' a ', ' b '], t._TextJustify('a b', 3))
    self.failUnlessEqual([' a ', ' b '], t._TextJustify('a  b', 3))
    self.failUnlessRaises(texttable.TableError, t._TextJustify, 'a', 2)
    self.failUnlessRaises(texttable.TableError, t._TextJustify, 'a bb', 3)
    self.failUnlessEqual([' a b  '], t._TextJustify('a\tb', 6))
    self.failUnlessEqual([' a  b '], t._TextJustify('a\t\tb', 6))
    self.failUnlessEqual([' a    ', ' b    '], t._TextJustify('a\nb\t', 6))

  def testSmallestColSize(self):
    t = texttable.TextTable()
    self.failUnlessEqual(1, t._SmallestColSize('a'))
    self.failUnlessEqual(2, t._SmallestColSize('a bb'))
    self.failUnlessEqual(4, t._SmallestColSize('a cccc bb'))
    self.failUnlessEqual(0, t._SmallestColSize(''))
    self.failUnlessEqual(1, t._SmallestColSize('a\tb'))
    self.failUnlessEqual(1, t._SmallestColSize('a\nb\tc'))
    self.failUnlessEqual(3, t._SmallestColSize('a\nbbb\n\nc'))
    # Check if _SmallestColSize is not influenced by ANSI colors.
    self.failUnlessEqual(
        3, t._SmallestColSize('bbb ' + terminal.AnsiText('bb', ['red'])))

  def testFormattedTableColor(self):
    # Test to sepcify the color defined in terminal.FG_COLOR_WORDS
    t = texttable.TextTable()
    t.header = ('LSP', 'Name')
    t.Append(('col1', 'col2'))
    for color_key in terminal.FG_COLOR_WORDS:
      t[0].color = terminal.FG_COLOR_WORDS[color_key]
      t.FormattedTable()
      self.failUnlessEqual(sorted(t[0].color),
                           sorted(terminal.FG_COLOR_WORDS[color_key]))
    for color_key in terminal.BG_COLOR_WORDS:
      t[0].color = terminal.BG_COLOR_WORDS[color_key]
      t.FormattedTable()
      self.failUnlessEqual(sorted(t[0].color),
                           sorted(terminal.BG_COLOR_WORDS[color_key]))

  def testFormattedTableColoredMultilineCells(self):
    t = texttable.TextTable()
    t.header = ('LSP', 'Name')
    t.Append((terminal.AnsiText('col1 boembabies', ['yellow']), 'col2'))
    t.Append(('col1', 'col2'))
    self.failUnlessEqual(
        ' LSP           Name \n'
        '====================\n'
        ' \033[33mcol1          col2 \n'
        ' boembabies\033[0m         \n'
        '--------------------\n'
        ' col1          col2 \n',
        t.FormattedTable(width=20))

  def testFormattedTableColoredCells(self):
    t = texttable.TextTable()
    t.header = ('LSP', 'Name')
    t.Append((terminal.AnsiText('col1', ['yellow']), 'col2'))
    t.Append(('col1', 'col2'))
    self.failUnlessEqual(
        ' LSP   Name \n'
        '============\n'
        ' \033[33mcol1\033[0m  col2 \n'
        ' col1  col2 \n',
        t.FormattedTable())

  def testFormattedTableColoredHeaders(self):
    t = texttable.TextTable()
    t.header = (terminal.AnsiText('LSP', ['yellow']), 'Name')
    t.Append(('col1', 'col2'))
    t.Append(('col1', 'col2'))
    self.failUnlessEqual(
        ' \033[33mLSP\033[0m   Name \n'
        '============\n'
        ' col1  col2 \n'
        ' col1  col2 \n',
        t.FormattedTable())

    self.failUnlessEqual(
        ' col1  col2 \n'
        ' col1  col2 \n',
        t.FormattedTable(display_header=False))

  def testFormattedTable(self):
    # Basic table has a single whitespace on each side of the max cell width.
    t = self._BasicTable()
    self.failUnlessEqual(
        ' a   b   c  \n'
        '============\n'
        ' 1   2   3  \n'
        ' 10  20  30 \n',
        t.FormattedTable())

    # An increase in a cell size (or header), increases the side of that column.
    t.AddColumn('Beer')
    self.failUnlessEqual(
        ' a   b   c   Beer \n'
        '==================\n'
        ' 1   2   3        \n'
        ' 10  20  30       \n',
        t.FormattedTable())

    self.failUnlessEqual(
        ' 1   2   3        \n'
        ' 10  20  30       \n',
        t.FormattedTable(display_header=False))

    # Multiple words are on one line while space permits.
    t.Remove(1)
    t.Append(('', '', '', 'James Squire'))
    self.failUnlessEqual(
        ' a   b   c   Beer         \n'
        '==========================\n'
        ' 10  20  30               \n'
        '             James Squire \n',
        t.FormattedTable())

    # Or split across rows if not enough space.
    # A '---' divider is inserted to give a delimiter for multiline data.
    self.failUnlessEqual(
        ' a   b   c   Beer   \n'
        '====================\n'
        ' 10  20  30         \n'
        '--------------------\n'
        '             James  \n'
        '             Squire \n',
        t.FormattedTable(20))

    # Not needed below the data if last line, is needed otherwise.
    t.Append(('1', '2', '3', '4'))
    self.failUnlessEqual(
        ' a   b   c   Beer   \n'
        '====================\n'
        ' 10  20  30         \n'
        '--------------------\n'
        '             James  \n'
        '             Squire \n'
        '--------------------\n'
        ' 1   2   3   4      \n',
        t.FormattedTable(20))

    # Multiple multi line columms.
    t.Remove(3)
    t.Append(('', 'A small essay with a longword here', '1', '2'))
    self.failUnlessEqual(
        ' a   b         c   Beer   \n'
        '==========================\n'
        ' 10  20        30         \n'
        '--------------------------\n'
        '                   James  \n'
        '                   Squire \n'
        '--------------------------\n'
        '     A small   1   2      \n'
        '     essay                \n'
        '     with a               \n'
        '     longword             \n'
        '     here                 \n',
        t.FormattedTable(26))

    # Available space is added to multiline columns proportionaly
    # i.e. a column with twice as much text gets twice the space.
    self.failUnlessEqual(
        ' a   b            c   Beer   \n'
        '=============================\n'
        ' 10  20           30         \n'
        '-----------------------------\n'
        '                      James  \n'
        '                      Squire \n'
        '-----------------------------\n'
        '     A small      1   2      \n'
        '     essay with              \n'
        '     a longword              \n'
        '     here                    \n',
        t.FormattedTable(29))

    # Display fails if the minimum size needed is not available.
    # These are both 1-char less than the minimum required.
    self.failUnlessRaises(texttable.TableError, t.FormattedTable, 25)
    t.Remove(3)
    t.Remove(2)
    self.failUnlessRaises(texttable.TableError, t.FormattedTable, 17)
    t.Append(('line\nwith\n\nbreaks', 'Line with\ttabs\t\t',
              'line with  lots of   spaces.', '4'))
    t[0].color = ['yellow']
    self.failUnlessEqual(
        '\033[33m a       b     c         Beer \n'
        '==============================\033[0m\n'
        ' 10      20    30             \n'
        '------------------------------\n'
        ' line    Line  line      4    \n'
        ' with    with  with           \n'
        '         tabs  lots of        \n'
        ' breaks        spaces.        \n',
        t.FormattedTable(30))

    t[0].color = None
    self.failUnlessEqual(
        ' a         b        c              Beer \n'
        '========================================\n'
        ' 10        20       30                  \n'
        '----------------------------------------\n'
        ' line      Line     line with      4    \n'
        ' with      with     lots of             \n'
        '           tabs     spaces.             \n'
        ' breaks                                 \n',
        t.FormattedTable(40))

  def testFormattedTable2(self):
    t = texttable.TextTable()
    t.header = ('Host', 'Interface', 'Admin', 'Oper', 'Proto', 'Address')
    t.Append(('DeviceA', 'lo0', 'up', 'up', '', []))
    t.Append(('DeviceA', 'lo0.0', 'up', 'up', 'inet',
              ['127.0.0.1', '10.100.100.1']))
    t.Append(('DeviceA', 'lo0.16384', 'up', 'up', 'inet', ['127.0.0.1']))
    t[-2].color = ['red']

    # pylint: disable-msg=C6310
    self.failUnlessEqual(
        ' Host     Interface  Admin  Oper  Proto  Address              \n'
        '==============================================================\n'
        ' DeviceA  lo0        up     up                                \n'
        '--------------------------------------------------------------\n'
        '\033[31m DeviceA  lo0.0      up     up    inet   127.0.0.1,           \n'
        '                                         10.100.100.1         \033[0m\n'
        '--------------------------------------------------------------\n'
        ' DeviceA  lo0.16384  up     up    inet   127.0.0.1            \n',
        t.FormattedTable(62))

    # Test with specific columns only
    self.failUnlessEqual(
        ' Host     Interface  Admin  Oper  Address                 \n'
        '==========================================================\n'
        ' DeviceA  lo0        up     up                            \n'
        '\033[31m DeviceA  lo0.0      up     up    127.0.0.1, 10.100.100.1 \033[0m\n'
        ' DeviceA  lo0.16384  up     up    127.0.0.1               \n',
        t.FormattedTable(62, columns=['Host', 'Interface', 'Admin', 'Oper', 'Address']))


  def testSortTable(self):
    def Maketable():
      t = texttable.TextTable()
      t.header = ('Col1', 'Col2', 'Col3')
      t.Append(('lorem', 'ipsum', 'dolor'))
      t.Append(('ut', 'enim', 'ad'))
      t.Append(('duis', 'aute', 'irure'))
      return t
    # Test basic sort
    table = Maketable()
    table.sort()
    self.assertEqual(['duis', 'aute', 'irure'], table[1].values)
    self.assertEqual(['lorem', 'ipsum', 'dolor'], table[2].values)
    self.assertEqual(['ut', 'enim', 'ad'], table[3].values)

    # Test with different key
    table = Maketable()
    table.sort(key=lambda x: x['Col2'])
    self.assertEqual(['duis', 'aute', 'irure'], table[1].values)
    self.assertEqual(['ut', 'enim', 'ad'], table[2].values)
    self.assertEqual(['lorem', 'ipsum', 'dolor'], table[3].values)

    # Multiple keys.
    table = Maketable()
    table.Append(('duis', 'aute', 'aute'))
    table.sort(key=lambda x: x['Col2', 'Col3'])
    self.assertEqual(['duis', 'aute', 'aute'], table[1].values)
    self.assertEqual(['duis', 'aute', 'irure'], table[2].values)

    # Test with custom compare
    # pylint: disable-msg=C6409
    def compare(a, b):
      # Compare from 2nd char of 1st col
      return cmp(a[0][1:], b[0][1:])
    table = Maketable()
    table.sort(cmp=compare)
    self.assertEqual(['lorem', 'ipsum', 'dolor'], table[1].values)
    self.assertEqual(['ut', 'enim', 'ad'], table[2].values)
    self.assertEqual(['duis', 'aute', 'irure'], table[3].values)
    # Set the key, so the 1st col compared is 'Col2'.
    table.sort(key=lambda x: x['Col2'], cmp=compare)
    self.assertEqual(['ut', 'enim', 'ad'], table[2].values)
    self.assertEqual(['lorem', 'ipsum', 'dolor'], table[1].values)
    self.assertEqual(['duis', 'aute', 'irure'], table[3].values)

    # Sort in reverse order.
    table.sort(key=lambda x: x['Col2'], reverse=True)
    self.assertEqual(['lorem', 'ipsum', 'dolor'], table[1].values)
    self.assertEqual(['ut', 'enim', 'ad'], table[2].values)
    self.assertEqual(['duis', 'aute', 'irure'], table[3].values)


if __name__ == '__main__':
  unittest.main()
