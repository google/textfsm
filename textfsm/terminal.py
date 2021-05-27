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

"""Simple terminal related routines."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

try:
  # Import fails on Windows machines.
  import fcntl
  import termios
  import tty
except (ImportError, ModuleNotFoundError):
  pass
import getopt
import os
import re
import struct
import sys
import time
from builtins import object   # pylint: disable=redefined-builtin
from builtins import str      # pylint: disable=redefined-builtin

__version__ = '0.1.1'

# ANSI, ISO/IEC 6429 escape sequences, SGR (Select Graphic Rendition) subset.
SGR = {
    'reset': 0,
    'bold': 1,
    'underline': 4,
    'blink': 5,
    'negative': 7,
    'underline_off': 24,
    'blink_off': 25,
    'positive': 27,
    'black': 30,
    'red': 31,
    'green': 32,
    'yellow': 33,
    'blue': 34,
    'magenta': 35,
    'cyan': 36,
    'white': 37,
    'fg_reset': 39,
    'bg_black': 40,
    'bg_red': 41,
    'bg_green': 42,
    'bg_yellow': 43,
    'bg_blue': 44,
    'bg_magenta': 45,
    'bg_cyan': 46,
    'bg_white': 47,
    'bg_reset': 49,
    }

# Provide a familar descriptive word for some ansi sequences.
FG_COLOR_WORDS = {'black': ['black'],
                  'dark_gray': ['bold', 'black'],
                  'blue': ['blue'],
                  'light_blue': ['bold', 'blue'],
                  'green': ['green'],
                  'light_green': ['bold', 'green'],
                  'cyan': ['cyan'],
                  'light_cyan': ['bold', 'cyan'],
                  'red': ['red'],
                  'light_red': ['bold', 'red'],
                  'purple': ['magenta'],
                  'light_purple': ['bold', 'magenta'],
                  'brown': ['yellow'],
                  'yellow': ['bold', 'yellow'],
                  'light_gray': ['white'],
                  'white': ['bold', 'white']}

BG_COLOR_WORDS = {'black': ['bg_black'],
                  'red': ['bg_red'],
                  'green': ['bg_green'],
                  'yellow': ['bg_yellow'],
                  'dark_blue': ['bg_blue'],
                  'purple': ['bg_magenta'],
                  'light_blue': ['bg_cyan'],
                  'grey': ['bg_white']}


# Characters inserted at the start and end of ANSI strings
# to provide hinting for readline and other clients.
ANSI_START = '\001'
ANSI_END = '\002'


sgr_re = re.compile(r'(%s?\033\[\d+(?:;\d+)*m%s?)' % (
    ANSI_START, ANSI_END))


class Error(Exception):
  """The base error class."""


class Usage(Error):
  """Command line format error."""


def _AnsiCmd(command_list):
  """Takes a list of SGR values and formats them as an ANSI escape sequence.

  Args:
    command_list: List of strings, each string represents an SGR value.
        e.g. 'fg_blue', 'bg_yellow'

  Returns:
    The ANSI escape sequence.

  Raises:
    ValueError: if a member of command_list does not map to a valid SGR value.
  """
  if not isinstance(command_list, list):
    raise ValueError('Invalid list: %s' % command_list)
  # Checks that entries are valid SGR names.
  # No checking is done for sequences that are correct but 'nonsensical'.
  for sgr in command_list:
    if sgr.lower() not in SGR:
      raise ValueError('Invalid or unsupported SGR name: %s' % sgr)
  # Convert to numerical strings.
  command_str = [str(SGR[x.lower()]) for x in command_list]
  # Wrap values in Ansi escape sequence (CSI prefix & SGR suffix).
  return '\033[%sm' % (';'.join(command_str))


def AnsiText(text, command_list=None, reset=True):
  """Wrap text in ANSI/SGR escape codes.

  Args:
    text: String to encase in sgr escape sequence.
    command_list: List of strings, each string represents an sgr value.
      e.g. 'fg_blue', 'bg_yellow'
    reset: Boolean, if to add a reset sequence to the suffix of the text.

  Returns:
    String with sgr characters added.
  """
  command_list = command_list or ['reset']
  if reset:
    return '%s%s%s' % (_AnsiCmd(command_list), text, _AnsiCmd(['reset']))
  else:
    return '%s%s' % (_AnsiCmd(command_list), text)


def StripAnsiText(text):
  """Strip ANSI/SGR escape sequences from text."""
  return sgr_re.sub('', text)


def EncloseAnsiText(text):
  """Enclose ANSI/SGR escape sequences with ANSI_START and ANSI_END."""
  return sgr_re.sub(lambda x: ANSI_START + x.group(1) + ANSI_END, text)


def TerminalSize():
  """Returns terminal length and width as a tuple."""
  try:
    with open(os.ctermid()) as tty_instance:
      length_width = struct.unpack(
          'hh', fcntl.ioctl(tty_instance.fileno(), termios.TIOCGWINSZ, '1234'))
  except (IOError, OSError, NameError):
    try:
      length_width = (int(os.environ['LINES']),
                      int(os.environ['COLUMNS']))
    except (ValueError, KeyError):
      length_width = (24, 80)
  return length_width


def LineWrap(text, omit_sgr=False):
  """Break line to fit screen width, factoring in ANSI/SGR escape sequences.

  Args:
    text: String to line wrap.
    omit_sgr: Bool, to omit counting ANSI/SGR sequences in the length.

  Returns:
    Text with additional line wraps inserted for lines grater than the width.
  """

  def _SplitWithSgr(text_line):
    """Tokenise the line so that the sgr sequences can be omitted."""
    token_list = sgr_re.split(text_line)
    text_line_list = []
    line_length = 0
    for (index, token) in enumerate(token_list):
      # Skip null tokens.
      if token == '':
        continue

      if sgr_re.match(token):
        # Add sgr escape sequences without splitting or counting length.
        text_line_list.append(token)
        text_line = ''.join(token_list[index +1:])
      else:
        if line_length + len(token) <= width:
          # Token fits in line and we count it towards overall length.
          text_line_list.append(token)
          line_length += len(token)
          text_line = ''.join(token_list[index +1:])
        else:
          # Line splits part way through this token.
          # So split the token, form a new line and carry the remainder.
          text_line_list.append(token[:width - line_length])
          text_line = token[width - line_length:]
          text_line += ''.join(token_list[index +1:])
          break

    return (''.join(text_line_list), text_line)

  # We don't use textwrap library here as it insists on removing
  # trailing/leading whitespace (pre 2.6).
  (_, width) = TerminalSize()
  text = str(text)
  text_multiline = []
  for text_line in text.splitlines():
    # Is this a line that needs splitting?
    while ((omit_sgr and (len(StripAnsiText(text_line)) > width)) or
           (len(text_line) > width)):
      # If there are no sgr escape characters then do a straight split.
      if not omit_sgr:
        text_multiline.append(text_line[:width])
        text_line = text_line[width:]
      else:
        (multiline_line, text_line) = _SplitWithSgr(text_line)
        text_multiline.append(multiline_line)
    if text_line:
      text_multiline.append(text_line)
  return '\n'.join(text_multiline)


class Pager(object):
  """A simple text pager module.

  Supports paging of text on a terminal, somewhat like a simple 'more' or
  'less', but in pure Python.

  The simplest usage:

    with open('file.txt') as f:
      s = f.read()
    Pager(s).Page()

  Particularly unique is the ability to sequentially feed new text into the
  pager:

    p = Pager()
    for line in socket.read():
      p.Page(line)

  If done this way, the Page() method will block until either the line has been
  displayed, or the user has quit the pager.

  Currently supported keybindings are:
    <enter> - one line down
    <down arrow> - one line down
    b - one page up
    <up arrow> - one line up
    q - Quit the pager
    g - scroll to the end
    <space> - one page down
  """

  def __init__(self, text=None, delay=None):
    """Constructor.

    Args:
      text: A string, the text that will be paged through.
      delay: A boolean, if True will cause a slight delay
        between line printing for more obvious scrolling.
    """
    self._text = text or ''
    self._delay = delay
    try:
      self._tty = open('/dev/tty')
    except IOError:
      # No TTY, revert to stdin
      self._tty = sys.stdin
    self.SetLines(None)
    self.Reset()

  def __del__(self):
    """Deconstructor, closes tty."""
    if getattr(self, '_tty', sys.stdin) is not sys.stdin:
      self._tty.close()

  def Reset(self):
    """Reset the pager to the top of the text."""
    self._displayed = 0
    self._currentpagelines = 0
    self._lastscroll = 1
    self._lines_to_show = self._cli_lines

  def SetLines(self, lines):
    """Set number of screen lines.

    Args:
      lines: An int, number of lines. If None, use terminal dimensions.

    Raises:
      ValueError, TypeError: Not a valid integer representation.
    """

    (self._cli_lines, self._cli_cols) = TerminalSize()

    if lines:
      self._cli_lines = int(lines)

  def Clear(self):
    """Clear the text and reset the pager."""
    self._text = ''
    self.Reset()

  def Page(self, text=None, show_percent=None):
    """Page text.

    Continues to page through any text supplied in the constructor. Also, any
    text supplied to this method will be appended to the total text to be
    displayed. The method returns when all available text has been displayed to
    the user, or the user quits the pager.

    Args:
      text: A string, extra text to be paged.
      show_percent: A boolean, if True, indicate how much is displayed so far.
        If None, this behaviour is 'text is None'.

    Returns:
      A boolean. If True, more data can be displayed to the user. False
        implies that the user has quit the pager.
    """
    if text is not None:
      self._text += text

    if show_percent is None:
      show_percent = text is None
    self._show_percent = show_percent

    text = LineWrap(self._text).splitlines()
    while True:
      # Get a list of new lines to display.
      self._newlines = text[self._displayed:self._displayed+self._lines_to_show]
      for line in self._newlines:
        sys.stdout.write(line + '\n')
        if self._delay and self._lastscroll > 0:
          time.sleep(0.005)
      self._displayed += len(self._newlines)
      self._currentpagelines += len(self._newlines)
      if self._currentpagelines >= self._lines_to_show:
        self._currentpagelines = 0
        wish = self._AskUser()
        if wish == 'q':         # Quit pager.
          return False
        elif wish == 'g':       # Display till the end.
          self._Scroll(len(text) - self._displayed + 1)
        elif wish == '\r':      #  Enter, down a line.
          self._Scroll(1)
        elif wish == '\033[B':  # Down arrow, down a line.
          self._Scroll(1)
        elif wish == '\033[A':  # Up arrow, up a line.
          self._Scroll(-1)
        elif wish == 'b':       # Up a page.
          self._Scroll(0 - self._cli_lines)
        else:                   # Next page.
          self._Scroll()
      if self._displayed >= len(text):
        break

    return True

  def _Scroll(self, lines=None):
    """Set attributes to scroll the buffer correctly.

    Args:
      lines: An int, number of lines to scroll. If None, scrolls
        by the terminal length.
    """
    if lines is None:
      lines = self._cli_lines

    if lines < 0:
      self._displayed -= self._cli_lines
      self._displayed += lines
      if self._displayed < 0:
        self._displayed = 0
      self._lines_to_show = self._cli_lines
    else:
      self._lines_to_show = lines

    self._lastscroll = lines

  def _AskUser(self):
    """Prompt the user for the next action.

    Returns:
      A string, the character entered by the user.
    """
    if self._show_percent:
      progress = int(self._displayed*100 / (len(self._text.splitlines())))
      progress_text = ' (%d%%)' % progress
    else:
      progress_text = ''
    question = AnsiText(
        'Enter: next line, Space: next page, '
        'b: prev page, q: quit.%s' %
        progress_text, ['green'])
    sys.stdout.write(question)
    sys.stdout.flush()
    ch = self._GetCh()
    sys.stdout.write('\r%s\r' % (' '*len(question)))
    sys.stdout.flush()
    return ch

  def _GetCh(self):
    """Read a single character from the user.

    Returns:
      A string, the character read.
    """
    fd = self._tty.fileno()
    old = termios.tcgetattr(fd)
    try:
      tty.setraw(fd)
      ch = self._tty.read(1)
      # Also support arrow key shortcuts (escape + 2 chars)
      if ord(ch) == 27:
        ch += self._tty.read(2)
    finally:
      termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch


def main(argv=None):
  """Routine to page text or determine window size via command line."""

  if argv is None:
    argv = sys.argv

  try:
    opts, args = getopt.getopt(argv[1:], 'dhs', ['nodelay', 'help', 'size'])
  except getopt.error as msg:
    raise Usage(msg)

  # Print usage and return, regardless of presence of other args.
  for opt, _ in opts:
    if opt in ('-h', '--help'):
      print(__doc__)
      print(help_msg)
      return 0

  isdelay = False
  for opt, _ in opts:
    # Prints the size of the terminal and returns.
    # Mutually exclusive to the paging of text and overrides that behaviour.
    if opt in ('-s', '--size'):
      print('Length: %d, Width: %d' % TerminalSize())
      return 0
    elif opt in ('-d', '--delay'):
      isdelay = True
    else:
      raise Usage('Invalid arguments.')

  # Page text supplied in either specified file or stdin.

  if len(args) == 1:
    with open(args[0], 'r') as f:
      fd = f.read()
  else:
    fd = sys.stdin.read()
  Pager(fd, delay=isdelay).Page()


if __name__ == '__main__':
  help_msg = '%s [--help] [--size] [--nodelay] [input_file]\n' % sys.argv[0]
  try:
    sys.exit(main())
  except Usage as err:
    print(err, file=sys.stderr)
    print('For help use --help', file=sys.stderr)
    sys.exit(2)
