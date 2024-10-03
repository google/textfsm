#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#

"""Unittest for terminal module."""

import sys
import unittest

from textfsm import terminal


class TerminalTest(unittest.TestCase):

  def setUp(self):
    super(TerminalTest, self).setUp()
    self._get_terminal_size_orig = terminal.shutil.get_terminal_size

  def tearDown(self):
    super(TerminalTest, self).tearDown()
    terminal.shutil.get_terminal_size = self._get_terminal_size_orig

  def testAnsiCmd(self):
    self.assertEqual('\033[0m', terminal._AnsiCmd(['reset']))
    self.assertEqual('\033[0m', terminal._AnsiCmd(['RESET']))
    self.assertEqual('\033[0;32m', terminal._AnsiCmd(['reset', 'Green']))
    self.assertRaises(ValueError, terminal._AnsiCmd, ['bogus'])
    self.assertRaises(ValueError, terminal._AnsiCmd, ['reset', 'bogus'])

  def testAnsiText(self):
    self.assertEqual('\033[0mhello world\033[0m',
                     terminal.AnsiText('hello world'))
    self.assertEqual('\033[31mhello world\033[0m',
                     terminal.AnsiText('hello world', ['red']))
    self.assertEqual('\033[31;46mhello world',
                     terminal.AnsiText(
                         'hello world', ['red', 'bg_cyan'], False))

  def testStripAnsi(self):
    text = 'ansi length'
    self.assertEqual(text, terminal.StripAnsiText(text))
    ansi_text = '\033[5;32;44mansi\033[0m length'
    self.assertEqual(text, terminal.StripAnsiText(ansi_text))

  def testEncloseAnsi(self):
    text = 'ansi length'
    self.assertEqual(text, terminal.EncloseAnsiText(text))
    ansi_text = '\033[5;32;44mansi\033[0m length'
    ansi_enclosed = '\001\033[5;32;44m\002ansi\001\033[0m\002 length'
    self.assertEqual(ansi_enclosed, terminal.EncloseAnsiText(ansi_text))

  def testLineWrap(self):
    terminal.shutil.get_terminal_size = lambda: (11, 5)
    text = ''
    self.assertEqual(text, terminal.LineWrap(text))
    text = 'one line'
    self.assertEqual(text, terminal.LineWrap(text))
    text = 'two\nlines'
    self.assertEqual(text, terminal.LineWrap(text))
    text = 'one line that is too long'
    text2 = 'one line th\nat is too l\nong'
    self.assertEqual(text2, terminal.LineWrap(text))
    # Counting ansi characters won't matter if there are none.
    self.assertEqual(text2, terminal.LineWrap(text, False))
    text = 'one line \033[5;32;44mthat\033[0m is too long with ansi'
    text2 = 'one line \033[5;32;44mth\nat\033[0m is too l\nong with an\nsi'
    text3 = 'one line \033[\n5;32;44mtha\nt\033[0m is to\no long with\n ansi'
    # Ansi does not factor and the line breaks stay the same.
    self.assertEqual(text2, terminal.LineWrap(text, True))
    # If we count the ansi escape as characters then the line breaks change.
    self.assertEqual(text3, terminal.LineWrap(text, False))
    # False is implicit default.
    self.assertEqual(text3, terminal.LineWrap(text))
    # Couple of edge cases where we split on token boundary.
    text4 = 'ooone line \033[5;32;44mthat\033[0m is too long with ansi'
    text5 = 'ooone line \033[5;32;44m\nthat\033[0m is too\n long with \nansi'
    self.assertEqual(text5, terminal.LineWrap(text4, True))
    text6 = 'e line \033[5;32;44mthat\033[0m is too long with ansi'
    text7 = 'e line \033[5;32;44mthat\033[0m\n is too lon\ng with ansi'
    self.assertEqual(text7, terminal.LineWrap(text6, True))

  def testIssue1(self):
    self.assertEqual(10, len(terminal.StripAnsiText('boembabies' '\033[0m')))
    terminal.TerminalSize = lambda: (10, 10)
    text1 = terminal.LineWrap('\033[32m' + 'boembabies, ' * 10 + 'boembabies' +
                              '\033[0m', omit_sgr=True)
    text2 = ('\033[32m' +
             terminal.LineWrap('boembabies, ' * 10 + 'boembabies') +
             '\033[0m')
    self.assertEqual(text1, text2)


class FakeTerminal(object):

  def __init__(self):
    self.output = ''

  # pylint: disable=C6409
  def write(self, text):
    self.output += text

  # pylint: disable=C6409
  def CountLines(self):
    return len(self.output.splitlines())

  def flush(self):
    pass


class PagerTest(unittest.TestCase):

  def setUp(self):
    super(PagerTest, self).setUp()
    sys.stdout = FakeTerminal()
    self.get_ch_orig = terminal.Pager._GetCh
    terminal.Pager._GetCh = lambda self: 'q'

    self.p = terminal.Pager()

  def tearDown(self):
    super(PagerTest, self).tearDown()
    terminal.Pager._GetCh = self.get_ch_orig
    sys.stdout = sys.__stdout__

  def testPager(self):

    self.p.Clear()
    self.assertEqual('', self.p._text)
    self.assertEqual(0, self.p._displayed)
    self.assertEqual(1, self.p._lastscroll)

  def testPage(self):
    txt = ''
    for i in range(100):
      txt += '%d a random line of text here\n' % i
    self.p._text = txt
    self.p.Page()
    self.assertEqual(self.p._cli_lines+2, sys.stdout.CountLines())

    sys.stdout.output = ''
    self.p = terminal.Pager()
    self.p._text = ''
    for _ in range(10):
      self.p._text += 'a' * 100 + '\n'
    self.p.Page()
    self.assertEqual(20, sys.stdout.CountLines())


if __name__ == '__main__':
  unittest.main()
