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

import getopt
import re
import shutil
import sys
import time
import typing

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
FG_COLOR_WORDS = {
    'black': ['black'],
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
    'white': ['bold', 'white'],
}

BG_COLOR_WORDS = {
    'black': ['bg_black'],
    'red': ['bg_red'],
    'green': ['bg_green'],
    'yellow': ['bg_yellow'],
    'dark_blue': ['bg_blue'],
    'purple': ['bg_magenta'],
    'light_blue': ['bg_cyan'],
    'grey': ['bg_white'],
}

# Characters inserted at the start and end of ANSI strings
# to provide hinting for readline and other clients.
ANSI_START = '\001'
ANSI_END = '\002'

# Arrow key sequences.
UP_ARROW = '\033[A'
DOWN_ARROW = '\033[B'

# Clear the screen and move the cursor to the top left.
CLEAR_SCREEN = '\033[2J\033[H'

# Navigational instructions for the user of the pager.
PROMPT_QUESTION = 'n: next line, Space: next page, b: prev page, q: quit.'


def _GetChar() -> str:
  """Read a single character from the tty.

  Returns:
    A string, the character read.
  """
  # Default to 'q' to quit out of paging content.
  return 'q'

try:
  # Import fails on Windows machines.
  # pylint: disable=g-import-not-at-top
  import termios
  import tty

  def _PosixGetChar() -> str:
    """Read a single character from the tty."""
    try:
      read_tty = open('/dev/tty')
    except IOError:
      # No TTY, revert to stdin
      read_tty = sys.stdin
    fd = read_tty.fileno()
    old = termios.tcgetattr(fd)
    try:
      tty.setraw(fd)
      ch = read_tty.read(1)
      # Also support arrow key shortcuts (escape + 2 chars)
      if ord(ch) == 27:
        ch += read_tty.read(2)
    finally:
      termios.tcsetattr(fd, termios.TCSADRAIN, old)
      if '_tty' != sys.stdin:
        read_tty.close()
    return ch
  _GetChar = _PosixGetChar
except (ImportError, ModuleNotFoundError):
  # If we are on MS Windows then try using msvcrt library instead.
  import msvcrt
  def _MSGetChar() -> str:
    ch = msvcrt.getch()                                                         # type: ignore
      # Also support arrow key shortcuts (escape + 2 chars)
    if ord(ch) == 27:
      ch += msvcrt.getch()                                                      # type: ignore
    return ch
  _GetChar = _MSGetChar

# Regular expression to match ANSI/SGR escape sequences.
sgr_re = re.compile(r'(%s?\033\[\d+(?:;\d+)*m%s?)' % (ANSI_START, ANSI_END))


class Error(Exception):
  """The base error class."""


class UsageError(Error):
  """Command line format error."""


def _AnsiCmd(command_list):
  """Takes a list of SGR values and formats them as an ANSI escape sequence.

  Args:
    command_list: List of strings, each string represents an SGR value. e.g.
      'fg_blue', 'bg_yellow'

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
  return '\033[%sm' % ';'.join(command_str)


def AnsiText(text, command_list=None, reset=True):
  """Wrap text in ANSI/SGR escape codes.

  Args:
    text: String to encase in sgr escape sequence.
    command_list: List of strings, each string represents an sgr value. e.g.
      'fg_blue', 'bg_yellow'
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


def LineWrap(text, omit_sgr=False):
  """Break line to fit screen width, factoring in ANSI/SGR escape sequences.

  Args:
    text: String to line wrap.
    omit_sgr: Bool, to omit counting ANSI/SGR sequences in the length.

  Returns:
    Text with additional line wraps inserted for lines grater than the width.
  """

  def _SplitWithSgr(text_line, width):
    """Tokenise the line so that the sgr sequences can be omitted."""
    token_list = sgr_re.split(text_line)
    text_line_list = []
    line_length = 0
    for index, token in enumerate(token_list):
      # Skip null tokens.
      if not token:
        continue

      if sgr_re.match(token):
        # Add sgr escape sequences without splitting or counting length.
        text_line_list.append(token)
        text_line = ''.join(token_list[index + 1 :])
      else:
        if line_length + len(token) <= width:
          # Token fits in line and we count it towards overall length.
          text_line_list.append(token)
          line_length += len(token)
          text_line = ''.join(token_list[index + 1 :])
        else:
          # Line splits part way through this token.
          # So split the token, form a new line and carry the remainder.
          text_line_list.append(token[: width - line_length])
          text_line = token[width - line_length :]
          text_line += ''.join(token_list[index + 1 :])
          break

    return (''.join(text_line_list), text_line)

  # We don't use textwrap library here as it insists on removing
  # trailing/leading whitespace (pre 2.6).
  (term_width, _) = shutil.get_terminal_size()
  text = str(text)
  text_multiline = []
  for text_line in text.splitlines():
    if not text_line:
      # Empty line, just add it.
      text_multiline.append(text_line)
      continue

    # Is this a line that needs splitting?
    while (omit_sgr and (len(StripAnsiText(text_line)) > term_width)) or (
        len(text_line) > term_width
    ):
      # If there are no sgr escape characters then do a straight split.
      if not omit_sgr:
        text_multiline.append(text_line[:term_width])
        text_line = text_line[term_width:]
      else:
        (multiline_line, text_line) = _SplitWithSgr(text_line, term_width)
        text_multiline.append(multiline_line)
    # If we have any text left over then add it.
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
    n - one line down
    <down arrow> - one line down
    b - one page up
    <up arrow> - one line up
    q - Quit the pager
    g - scroll to the end
    <space> - one page down
  """

  def __init__(self, text: str = '', delay: bool = False) -> None:
    """Constructor.

    Args:
      text: A string, the text that will be paged through.
      delay: A boolean, if True will cause a slight delay between line printing
        for more obvious scrolling.
    """
    self._text = text
    self.Reset()
    self.SetLines()
    # Add 0.005 sec delay between lines.
    if delay:
      self._delay = 0.005
    else:
      self._delay = 0

  def Reset(self) -> None:
    """Reset the pager to the top of the text."""
    self.first_line = 0

  def SetLines(self, num_lines: int = 0) -> typing.Tuple[int, int]:
    """Set number of lines to display at a time.

    Args:
      num_lines: An int, number of lines. If 0 use terminal dimensions.
        Maximum number should be one less than full terminal height,
        to allow for a user prompt. 

    Raises:
      ValueError, TypeError: Not a valid integer representation.

    Returns:
      Tuple, the width and lines of the terminal.
    """

    # Get the terminal size.
    (cols, lines) = shutil.get_terminal_size()
    # If we want paging by other than a whole window height.
    # For a whole window height, we drop one line to leave room for prompting.
    self._lines = int(num_lines) or lines - 1
    # Must be at least two rows, one row of output and one for the prompt.
    self._lines = max(2, self._lines)
    # Only number of rows is user configurable, we keep the terminal width.
    self._cols = cols
    return (self._cols, self._lines)

  def Clear(self) -> None:
    """Clear the text and reset the pager."""
    self._text = ''
    self.Reset()

  def _Display(self, start: int, length: int = 0
               ) -> typing.Tuple[int, float, int]:
    """Display a range of lines from the text.

    Args:
      start: An int, the first line to display.
      length: An int, the number of lines to display.
    Returns:
      Tuple, the next line after, and a percentage for where that line is.
    """

    # Break text on newlines. But also break on line wrap.
    text_list = LineWrap(self._text).splitlines()
    total_length = len(text_list)

    # Bound start and end to be within the text.
    start = max(0, start)
    # If open-ended, trim to be whole of text.
    if not length:
      end = total_length
    else:
      end = min(start + length, total_length)

    self._WriteOut(CLEAR_SCREEN)
    for i in range(start, end):
      print(text_list[i])
      if self._delay:
        time.sleep(self._delay)

    return (end, end / len(text_list) * 100, total_length)

  def _WriteOut(self, text: str) -> None:
    """Write text to stdout."""
    sys.stdout.write(text)
    sys.stdout.flush()

  def Page(self, more_text: str = '') -> None:
    """Page text.

    Continues to page through any text supplied in the constructor. Also, any
    text supplied to this method will be appended to the total text to be
    displayed. The method returns when all available text has been displayed to
    the user, or the user quits the pager.

    Args:
      more_text: A string, extra text to be appended.

    Returns:
      A boolean: True: we have reached the end. False: the user has quit early. 
    """

    # With each page, more text can be added.
    if more_text:
      self._text += more_text

    only_quit = False
    # Display a page of output.
    (end, percent, total_length) = self._Display(self.first_line, self._lines)
    # If less than a page to display, then 'quit' is only navigation option.
    if total_length < self._lines:
      only_quit = True

    # While there is more text to be displayed.
    while True:
      # If we are not reading streamed data then show % completion.
      if not more_text:
        wish = self._PromptUser(' (%d%%)' % percent)
      else:
        # If we are reading streamed data then show the prompt only.
        wish = self._PromptUser()

      if wish == 'q':           # Quit.
        break

      if only_quit:
        # If we have less than a page of text, ignore navigational keys.
        continue

      if wish == 'g':           # Display the remaining content.
        (end, _, total_length) = self._Display(end)
        self.first_line = end - self._lines
      elif wish == 'n':
        # Enter, down a line.
        self.first_line += 1
      elif wish == DOWN_ARROW:
        # Down a line.
        self.first_line += 1
      elif wish == UP_ARROW:
        # Up a line.
        self.first_line -= 1
      elif wish == 'b':
        # Up a page.
        self.first_line -= self._lines
      else:
        # Down a page.
        self.first_line += self._lines

      # Bound the first line to be within the text.
      self.first_line = max(0, self.first_line)
      self.first_line = min(total_length-self._lines, self.first_line)
      # Display a page of output.
      (end, percent, total_length) = self._Display(
          self.first_line, self._lines)

    # Set first_line to the end, so when we next page we start from there.
    self.first_line = end

  def _Prompt(self, suffix='') -> str:
    question = PROMPT_QUESTION + suffix
    # Truncate prompt to width of display.
    question = question[:self._cols]
    # Colorize the prompt.
    return AnsiText(question, ['green'])

  def _ClearPrompt(self) -> str:
    """Clear the prompt by over printing blank characters."""
    return '\r%s\r' % (' ' * self._cols)

  def _PromptUser(self, suffix='') -> str:
    """Prompt the user for the next action.

    Args:
      suffix: A string, to be appended to the prompt.

    Returns:
      A string, the character entered by the user.
    """

    self._WriteOut(self._Prompt(suffix))
    ch = _GetChar()
    self._WriteOut(self._ClearPrompt())
    return ch


def main(argv=None):
  """Routine to page text or determine window size via command line."""

  if argv is None:
    argv = sys.argv

  try:
    opts, args = getopt.getopt(argv[1:], 'dhs', ['nodelay', 'help', 'size'])
  except getopt.error as exc:
    raise UsageError(exc) from exc

  # Print usage and return, regardless of presence of other args.
  for opt, _ in opts:
    if opt in ('-h', '--help'):
      print(__doc__)
      print(help_msg)
      return 0

  is_delay = False
  for opt, _ in opts:
    # Prints the size of the terminal and returns.
    # Mutually exclusive to the paging of text and overrides that behavior.
    if opt in ('-s', '--size'):
      print('Width: %d, Length: %d' % shutil.get_terminal_size())
      return 0
    elif opt in ('-d', '--delay'):
      is_delay = True
    else:
      raise UsageError('Invalid arguments.')

  # Page text supplied in either specified file or stdin.

  if len(args) == 1:
    with open(args[0], 'r') as f:
      fd = f.read()
  else:
    fd = sys.stdin.read()
  Pager(fd, delay=is_delay).Page()


if __name__ == '__main__':
  help_msg = '%s [--help] [--size] [--nodelay] [input_file]\n' % sys.argv[0]
  try:
    sys.exit(main())
  except UsageError as err:
    print(err, file=sys.stderr)
    print('For help use --help', file=sys.stderr)
    sys.exit(2)
