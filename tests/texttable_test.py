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

"""Unittest for text table."""

import io
import unittest
from textfsm import terminal
from textfsm import texttable


def cmp(a, b):
  return (a > b) - (a < b)


class UnitTestRow(unittest.TestCase):
  """Tests texttable.Row() class."""

  def setUp(self):
    super(UnitTestRow, self).setUp()
    self.row = texttable.Row()
    self.row._keys = ['a', 'b', 'c']
    self.row._values = ['1', '2', '3']
    self.row._BuildIndex()

  def testRowBasicMethods(self):
    row = texttable.Row()
    # Setting columns (__setitem__).
    row['a'] = 'one'
    row['b'] = 'two'
    row['c'] = 'three'

    # Access a single column (__getitem__).
    self.assertEqual('one', row['a'])
    self.assertEqual('two', row['b'])
    self.assertEqual('three', row['c'])

    # Access multiple columns (__getitem__).
    self.assertEqual(['one', 'three'], row[('a', 'c')])
    self.assertEqual(['two', 'three'], row[('b', 'c')])

    # Access integer indexes (__getitem__).
    self.assertEqual('one', row[0])
    self.assertEqual(['two', 'three'], row[1:])

    # Test "get".
    self.assertEqual('one', row.get('a'))
    self.assertEqual('one', row.get('a', 'four'))
    self.assertEqual('four', row.get('d', 'four'))
    self.assertIsNone(row.get('d'))

    self.assertEqual(['one', 'three'], row.get(('a', 'c'), 'four'))
    self.assertEqual(['one', 'four'], row.get(('a', 'd'), 'four'))
    self.assertEqual(['one', None], row.get(('a', 'd')))

    self.assertEqual('one', row.get(0, 'four'))
    self.assertEqual('four', row.get(3, 'four'))
    self.assertIsNone(row.get(3))

    # Change existing column value.
    row['b'] = 'Two'
    self.assertEqual('Two', row['b'])

    # Length.
    self.assertEqual(3, len(row))

    # Contains.
    self.assertNotIn('two', row)
    self.assertIn('Two', row)

    # Iteration.
    self.assertEqual(['one', 'Two', 'three'], list(row))

  def testRowPublicMethods(self):
    self.row.header = ('x', 'y', 'z')
    # Header should be set, values initialised to None.
    self.assertEqual(['x', 'y', 'z'], self.row.header)
    self.assertEqual(['1', '2', '3'], self.row.values)
    row = texttable.Row()
    row.header = ('x', 'y', 'z')
    self.assertEqual(['x', 'y', 'z'], row.header)
    self.assertEqual([None, None, None], row.values)

  def testSetValues(self):
    """Tests setting row values from 'From' method."""

    # Set values from Dict.
    self.row._SetValues({'a': 'seven', 'b': 'eight', 'c': 'nine'})
    self.assertEqual(['seven', 'eight', 'nine'], self.row._values)
    self.row._SetValues({'b': '8', 'a': '7', 'c': '9'})
    self.assertEqual(['7', '8', '9'], self.row._values)

    # Converts integers to string equivalents.
    # Excess key/value pairs are ignored.
    self.row._SetValues({'a': 1, 'b': 2, 'c': 3, 'd': 4})
    self.assertEqual(['1', '2', '3'], self.row._values)

    # Values can come from a list of equal length the the keys.
    self.row._SetValues((7, '8', 9))
    self.assertEqual(['7', '8', '9'], self.row._values)

    # Or from a tuple of the same length.
    self.row._SetValues(('vb', 'coopers', 'squires'))
    self.assertEqual(['vb', 'coopers', 'squires'], self.row._values)

    # Raise error if list length is incorrect.
    self.assertRaises(TypeError, self.row._SetValues,
                      ['seven', 'eight', 'nine', 'ten'])
    # Raise error if row object has mismatched header.
    row = texttable.Row()
    self.row._keys = ['a']
    self.row._values = ['1']
    self.assertRaises(TypeError, self.row._SetValues, row)
    # Raise error if assigning wrong data type.
    self.assertRaises(TypeError, row._SetValues, 'abc')

  def testHeader(self):
    """Tests value property."""
    self.row.header = ('x', 'y', 'z')
    self.assertEqual(['x', 'y', 'z'], self.row.header)
    self.assertRaises(ValueError, self.row._SetHeader, ('a', 'b', 'c', 'd'))

  def testValue(self):
    """Tests value property."""
    self.row.values = {'a': 'seven', 'b': 'eight', 'c': 'nine'}
    self.assertEqual(['seven', 'eight', 'nine'], self.row.values)
    self.row.values = (7, '8', 9)
    self.assertEqual(['7', '8', '9'], self.row.values)

  def testIndex(self):
    """Tests Insert and Index methods."""

    self.assertEqual(1, self.row.index('b'))
    self.assertRaises(ValueError, self.row.index, 'bogus')

    # Insert element within row.
    self.row.Insert('black', 'white', 1)
    self.row.Insert('red', 'yellow', -1)
    self.assertEqual(['a', 'black', 'b', 'red', 'c'], self.row.header)
    self.assertEqual(['1', 'white', '2', 'yellow', '3'], self.row.values)
    self.assertEqual(1, self.row.index('black'))
    self.assertEqual(2, self.row.index('b'))
    self.assertRaises(IndexError, self.row.Insert, 'grey', 'gray', 6)
    self.assertRaises(IndexError, self.row.Insert, 'grey', 'gray', -7)


class MyRow(texttable.Row):
  pass


class UnitTestTextTable(unittest.TestCase):

  # pylint: disable=invalid-name
  def BasicTable(self):
    t = texttable.TextTable()
    t.header = ('a', 'b', 'c')
    t.Append(('1', '2', '3'))
    t.Append(('10', '20', '30'))
    return t

  def testFilter(self):
    old_table = self.BasicTable()
    filtered_table = old_table.Filter(
        function=lambda row: row['a'] == '10')
    self.assertEqual(1, filtered_table.size)

  def testFilterNone(self):
    t = texttable.TextTable()
    t.header = ('a', 'b', 'c')
    t.Append(('', '', []))
    filtered_table = t.Filter()
    self.assertEqual(0, filtered_table.size)

  def testMap(self):
    old_table = self.BasicTable()
    filtered_table = old_table.Map(
        function=lambda row: row['a'] == '10' and row)
    self.assertEqual(1, filtered_table.size)

  def testCustomRow(self):
    table = texttable.TextTable()
    table.header = ('a', 'b', 'c')
    self.assertEqual(type(texttable.Row()), type(table[0]))
    table = texttable.TextTable(row_class=MyRow)
    self.assertEqual(MyRow, table.row_class)
    table.header = ('a', 'b', 'c')
    self.assertEqual(type(MyRow()), type(table[0]))

  def testTableRepr(self):
    self.assertEqual(
        "TextTable('a, b, c\\n1, 2, 3\\n10, 20, 30\\n')",
        repr(self.BasicTable()))

  def testTableStr(self):
    self.assertEqual('a, b, c\n1, 2, 3\n10, 20, 30\n',
                     self.BasicTable().__str__())

  def testTableSetRow(self):
    t = self.BasicTable()
    t.Append(('one', 'two', 'three'))
    self.assertEqual(['one', 'two', 'three'], t[3].values)
    self.assertEqual(3, t.size)

  def testTableRowTypes(self):
    t = self.BasicTable()
    t.Append(('one', ['two', None], None))
    self.assertEqual(['one', ['two', 'None'], 'None'], t[3].values)
    self.assertEqual(3, t.size)

  def testTableRowDictWithInt(self):
    t = self.BasicTable()
    t.Append({'a': 1, 'b': 'two', 'c': 3})
    self.assertEqual(['1', 'two', '3'], t[3].values)
    self.assertEqual(3, t.size)

  def testTableRowListWithInt(self):
    t = self.BasicTable()
    t.Append([1, 'two', 3])
    self.assertEqual(['1', 'two', '3'], t[3].values)
    self.assertEqual(3, t.size)

  def testTableGetRow(self):
    t = self.BasicTable()
    self.assertEqual(['1', '2', '3'], t[1].values)
    self.assertEqual(['1', '3'], t[1][('a', 'c')])
    self.assertEqual('3', t[1][('c')])
    for rnum in range(t.size):
      self.assertEqual(rnum, t[rnum].row)

  def testTableRowWith(self):
    t = self.BasicTable()
    self.assertEqual(t.RowWith('a', '10'), t[2])
    self.assertRaises(IndexError, t.RowWith, 'g', '5')

  def testContains(self):
    t = self.BasicTable()
    self.assertIn('a', t)
    self.assertNotIn('x', t)

  def testIteration(self):
    t = self.BasicTable()
    index = 0
    for r in t:
      index += 1
      self.assertEqual(r, t[index])
      self.assertEqual(index, r.table._iterator)

    # Have we iterated over all entries.
    self.assertEqual(index, t.size)
    # The iterator count is reset.
    self.assertEqual(0, t._iterator)

    # Can we iterate repeatedly.
    index = 0
    index2 = 0
    for r in t:
      index += 1
      self.assertEqual(r, t[index])

    index1 = 0
    try:
      for r in t:
        index1 += 1
        index2 = 0
        self.assertEqual(index1, r.table._iterator)
        # Test nesting of iterations.
        for r2 in t:
          index2 += 1
          self.assertEqual(index2, r2.table._iterator)
          # Preservation of outer iterator after 'break'.
          if index1 == 2 and index2 == 2:
            break
        if index1 == 2:
          # Restoration of initial iterator after exception.
          raise IndexError
        self.assertEqual(index1, r.table._iterator)
    except IndexError:
      pass

    # Have we iterated over all entries - twice.
    self.assertEqual(index, t.size)
    self.assertEqual(index2, t.size)
    # The iterator count is reset.
    self.assertEqual(0, t._iterator)

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
    f = io.StringIO(buf)
    t = texttable.TextTable()
    self.assertEqual(2, t.CsvToTable(f))
    # pylint: disable=E1101
    self.assertEqual(['a', 'b', 'c', 'd'], t.header.values)
    self.assertEqual(['1', '2', '3', '4'], t[1].values)
    self.assertEqual(['5', '6', '7', '8'], t[2].values)
    self.assertEqual(2, t.size)

  def testHeaderIndex(self):
    t = self.BasicTable()
    self.assertEqual('c', t.header[2])
    self.assertEqual('a', t.header[0])

  def testAppend(self):
    t = self.BasicTable()
    t.Append(['10', '20', '30'])
    self.assertEqual(3, t.size)
    self.assertEqual(['10', '20', '30'], t[3].values)

    t.Append(('100', '200', '300'))
    self.assertEqual(4, t.size)
    self.assertEqual(['100', '200', '300'], t[4].values)

    t.Append(t[1])
    self.assertEqual(5, t.size)
    self.assertEqual(['1', '2', '3'], t[5].values)

    t.Append({'a': '11', 'b': '12', 'c': '13'})
    self.assertEqual(6, t.size)
    self.assertEqual(['11', '12', '13'], t[6].values)

    # The row index and container table should be set on new rows.
    self.assertEqual(6, t[6].row)
    self.assertEqual(t[1].table, t[6].table)

    self.assertRaises(TypeError, t.Append, ['20', '30'])
    self.assertRaises(TypeError, t.Append, ('1', '2', '3', '4'))
    self.assertRaises(TypeError, t.Append,
                      {'a': '11', 'b': '12', 'd': '13'})

  def testDeleteRow(self):
    t = self.BasicTable()
    self.assertEqual(2, t.size)
    t.Remove(1)
    self.assertEqual(['10', '20', '30'], t[1].values)
    for row in t:
      self.assertEqual(row, t[row.row])
    t.Remove(1)
    self.assertFalse(t.size)

  def testRowNumberandParent(self):
    t = self.BasicTable()
    t.Append(['10', '20', '30'])
    t.Remove(1)
    for rownum, row in enumerate(t, start=1):
      self.assertEqual(row.row, rownum)
      self.assertEqual(row.table, t)
    t2 = self.BasicTable()
    t.table = t2
    for rownum, row in enumerate(t, start=1):
      self.assertEqual(row.row, rownum)
      self.assertEqual(row.table, t)

  def testAddColumn(self):
    t = self.BasicTable()
    t.AddColumn('Beer')
    # pylint: disable=E1101
    self.assertEqual(['a', 'b', 'c', 'Beer'], t.header.values)
    self.assertEqual(['10', '20', '30', ''], t[2].values)

    t.AddColumn('Wine', default='Merlot', col_index=1)
    self.assertEqual(['a', 'Wine', 'b', 'c', 'Beer'], t.header.values)
    self.assertEqual(['10', 'Merlot', '20', '30', ''], t[2].values)

    t.AddColumn('Spirits', col_index=-2)
    self.assertEqual(['a', 'Wine', 'b', 'Spirits', 'c', 'Beer'],
                     t.header.values)
    self.assertEqual(['10', 'Merlot', '20', '', '30', ''], t[2].values)

    self.assertRaises(IndexError, t.AddColumn, 'x', col_index=6)
    self.assertRaises(IndexError, t.AddColumn, 'x', col_index=-7)
    self.assertRaises(texttable.TableError, t.AddColumn, 'b')

  def testAddTable(self):
    t = self.BasicTable()
    t2 = self.BasicTable()
    t3 = t + t2
    # pylint: disable=E1101
    self.assertEqual(['a', 'b', 'c'], t3.header.values)
    self.assertEqual(['10', '20', '30'], t3[2].values)
    self.assertEqual(['10', '20', '30'], t3[4].values)
    self.assertEqual(4, t3.size)

  def testExtendTable(self):
    t2 = self.BasicTable()
    t2.AddColumn('Beer')
    t2[1]['Beer'] = 'Lager'
    t2[1]['three'] = 'three'
    t2.Append(('one', 'two', 'three', 'Stout'))

    t = self.BasicTable()
    # Explicit key, use first column.
    t.extend(t2, ('a',))
    # pylint: disable=E1101
    self.assertEqual(['a', 'b', 'c', 'Beer'], t.header.values)
    # Only new columns have updated values.
    self.assertEqual(['1', '2', '3', 'Lager'], t[1].values)
    # All rows are extended.
    self.assertEqual(['10', '20', '30', ''], t[2].values)
    # The third row of 't2', is not included as there is no matching
    # row with the same key in the first table 't'.
    self.assertEqual(2, t.size)

    # pylint: disable=E1101
    t = self.BasicTable()
    # If a Key is non-unique (which is a soft-error), then the first instance
    # on the RHS is used for and applied to all non-unique entries on the LHS.
    t.Append(('1', '2b', '3b'))
    t2.Append(('1', 'two', '', 'Ale'))
    t.extend(t2, ('a',))
    self.assertEqual(['1', '2', '3', 'Lager'], t[1].values)
    self.assertEqual(['1', '2b', '3b', 'Lager'], t[3].values)

    t = self.BasicTable()
    # No explicit key, row number is used as the key.
    t.extend(t2)
    self.assertEqual(['a', 'b', 'c', 'Beer'], t.header.values)
    # Since row is key we pick up new values from corresponding row number.
    self.assertEqual(['1', '2', '3', 'Lager'], t[1].values)
    # All rows are still extended.
    self.assertEqual(['10', '20', '30', ''], t[2].values)
    # The third/fourth row of 't2', is not included as there is no corresponding
    # row in the first table 't'.
    self.assertEqual(2, t.size)

    t = self.BasicTable()
    t.Append(('1', 'two', '3'))
    t.Append(('two', '1', 'three'))
    t2 = texttable.TextTable()
    t2.header = ('a', 'b', 'c', 'Beer')
    t2.Append(('1', 'two', 'three', 'Stout'))
    # Explicitly declare which columns constitute the key.
    # Sometimes more than one row is needed to define a unique key (superkey).
    t.extend(t2, ('a', 'b'))

    self.assertEqual(['a', 'b', 'c', 'Beer'], t.header.values)
    # key '1', '2' does not equal '1', 'two', so column unmatched.
    self.assertEqual(['1', '2', '3', ''], t[1].values)
    # '1', 'two' matches but 'two', '1' does not as order is important.
    self.assertEqual(['1', 'two', '3', 'Stout'], t[3].values)
    self.assertEqual(['two', '1', 'three', ''], t[4].values)
    self.assertEqual(4, t.size)

    # Expects a texttable as the argument.
    self.assertRaises(AttributeError, t.extend, ['a', 'list'])
    # All Key column Names must be valid.
    self.assertRaises(IndexError, t.extend, ['a', 'list'], ('a', 'bogus'))

  def testTableWithLabels(self):
    t = self.BasicTable()
    self.assertEqual(
        '# LABEL a\n1.b 2\n1.c 3\n10.b 20\n10.c 30\n',
        t.LabelValueTable())
    self.assertEqual(
        '# LABEL a\n1.b 2\n1.c 3\n10.b 20\n10.c 30\n',
        t.LabelValueTable(['a']))
    self.assertEqual(
        '# LABEL a.c\n1.3.b 2\n10.30.b 20\n',
        t.LabelValueTable(['a', 'c']))
    self.assertEqual(
        '# LABEL a.c\n1.3.b 2\n10.30.b 20\n',
        t.LabelValueTable(['c', 'a']))
    self.assertRaises(texttable.TableError, t.LabelValueTable, ['a', 'z'])

  def testTextJustify(self):
    t = texttable.TextTable()
    self.assertEqual([' a    '], t._TextJustify('a', 6))
    self.assertEqual([' a b  '], t._TextJustify('a b', 6))
    self.assertEqual([' a  b '], t._TextJustify('a  b', 6))
    self.assertEqual([' a ', ' b '], t._TextJustify('a b', 3))
    self.assertEqual([' a ', ' b '], t._TextJustify('a  b', 3))
    self.assertRaises(texttable.TableError, t._TextJustify, 'a', 2)
    self.assertRaises(texttable.TableError, t._TextJustify, 'a bb', 3)
    self.assertEqual([' a b  '], t._TextJustify('a\tb', 6))
    self.assertEqual([' a  b '], t._TextJustify('a\t\tb', 6))
    self.assertEqual([' a    ', ' b    '], t._TextJustify('a\nb\t', 6))

  def testSmallestColSize(self):
    t = texttable.TextTable()
    self.assertEqual(1, t._SmallestColSize('a'))
    self.assertEqual(2, t._SmallestColSize('a bb'))
    self.assertEqual(4, t._SmallestColSize('a cccc bb'))
    self.assertEqual(0, t._SmallestColSize(''))
    self.assertEqual(1, t._SmallestColSize('a\tb'))
    self.assertEqual(1, t._SmallestColSize('a\nb\tc'))
    self.assertEqual(3, t._SmallestColSize('a\nbbb\n\nc'))
    # Check if _SmallestColSize is not influenced by ANSI colors.
    self.assertEqual(
        3, t._SmallestColSize('bbb ' + terminal.AnsiText('bb', ['red'])))

  def testFormattedTableColor(self):
    # Test to specify the color defined in terminal.FG_COLOR_WORDS
    t = texttable.TextTable()
    t.header = ('LSP', 'Name')
    t.Append(('col1', 'col2'))
    for color_key in terminal.FG_COLOR_WORDS:
      t[0].color = terminal.FG_COLOR_WORDS[color_key]
      t.FormattedTable()
      self.assertEqual(sorted(t[0].color),
                       sorted(terminal.FG_COLOR_WORDS[color_key]))
    for color_key in terminal.BG_COLOR_WORDS:
      t[0].color = terminal.BG_COLOR_WORDS[color_key]
      t.FormattedTable()
      self.assertEqual(sorted(t[0].color),
                       sorted(terminal.BG_COLOR_WORDS[color_key]))

  def testFormattedTableColoredMultilineCells(self):
    t = texttable.TextTable()
    t.header = ('LSP', 'Name')
    t.Append((terminal.AnsiText('col1 boembabies', ['yellow']), 'col2'))
    t.Append(('col1', 'col2'))
    self.assertEqual(
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
    self.assertEqual(
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
    self.assertEqual(
        ' \033[33mLSP\033[0m   Name \n'
        '============\n'
        ' col1  col2 \n'
        ' col1  col2 \n',
        t.FormattedTable())

    self.assertEqual(
        ' col1  col2 \n'
        ' col1  col2 \n',
        t.FormattedTable(display_header=False))

  def testFormattedTable(self):
    # Basic table has a single whitespace on each side of the max cell width.
    t = self.BasicTable()
    self.assertEqual(
        ' a   b   c  \n'
        '============\n'
        ' 1   2   3  \n'
        ' 10  20  30 \n',
        t.FormattedTable())

    # An increase in a cell size (or header), increases the side of that column.
    t.AddColumn('Beer')
    self.assertEqual(
        ' a   b   c   Beer \n'
        '==================\n'
        ' 1   2   3        \n'
        ' 10  20  30       \n',
        t.FormattedTable())

    self.assertEqual(
        ' 1   2   3        \n'
        ' 10  20  30       \n',
        t.FormattedTable(display_header=False))

    # Multiple words are on one line while space permits.
    t.Remove(1)
    t.Append(('', '', '', 'James Squire'))
    self.assertEqual(
        ' a   b   c   Beer         \n'
        '==========================\n'
        ' 10  20  30               \n'
        '             James Squire \n',
        t.FormattedTable())

    # Or split across rows if not enough space.
    # A '---' divider is inserted to give a delimiter for multiline data.
    self.assertEqual(
        ' a   b   c   Beer   \n'
        '====================\n'
        ' 10  20  30         \n'
        '--------------------\n'
        '             James  \n'
        '             Squire \n',
        t.FormattedTable(20))

    # Not needed below the data if last line, is needed otherwise.
    t.Append(('1', '2', '3', '4'))
    self.assertEqual(
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
    self.assertEqual(
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
    self.assertEqual(
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
    self.assertRaises(texttable.TableError, t.FormattedTable, 25)
    t.Remove(3)
    t.Remove(2)
    self.assertRaises(texttable.TableError, t.FormattedTable, 17)
    t.Append(('line\nwith\n\nbreaks', 'Line with\ttabs\t\t',
              'line with  lots of   spaces.', '4'))
    t[0].color = ['yellow']
    self.assertEqual(
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
    self.assertEqual(
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

    # pylint: disable=C6310
    self.assertEqual(
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
    self.assertEqual(
        ' Host     Interface  Admin  Oper  Address                 \n'
        '==========================================================\n'
        ' DeviceA  lo0        up     up                            \n'
        '\033[31m DeviceA  lo0.0      up     up    127.0.0.1, 10.100.100.1 \033[0m\n'
        ' DeviceA  lo0.16384  up     up    127.0.0.1               \n',
        t.FormattedTable(62, columns=['Host', 'Interface', 'Admin', 'Oper', 'Address']))

  def testSortTable(self):
    # pylint: disable=invalid-name
    def MakeTable():
      t = texttable.TextTable()
      t.header = ('Col1', 'Col2', 'Col3')
      t.Append(('lorem', 'ipsum', 'dolor'))
      t.Append(('ut', 'enim', 'ad'))
      t.Append(('duis', 'aute', 'irure'))
      return t
    # Test basic sort
    table = MakeTable()
    table.sort()
    self.assertEqual(['duis', 'aute', 'irure'], table[1].values)
    self.assertEqual(['lorem', 'ipsum', 'dolor'], table[2].values)
    self.assertEqual(['ut', 'enim', 'ad'], table[3].values)

    # Test with different key
    table = MakeTable()
    table.sort(key=lambda x: x['Col2'])
    self.assertEqual(['duis', 'aute', 'irure'], table[1].values)
    self.assertEqual(['ut', 'enim', 'ad'], table[2].values)
    self.assertEqual(['lorem', 'ipsum', 'dolor'], table[3].values)

    # Multiple keys.
    table = MakeTable()
    table.Append(('duis', 'aute', 'aute'))
    table.sort(key=lambda x: x['Col2', 'Col3'])
    self.assertEqual(['duis', 'aute', 'aute'], table[1].values)
    self.assertEqual(['duis', 'aute', 'irure'], table[2].values)

    # Test with custom compare
    # pylint: disable=C6409
    def compare(a, b):
      # Compare from 2nd char of 1st col
      return cmp(a[0][1:], b[0][1:])
    table = MakeTable()
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
