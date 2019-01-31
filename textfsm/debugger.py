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

""" Visual Debugger

Provides a HTML-based debugging tool that allows authors of templates
to view the behavior of templates when applied to some example CLI text.
State changes are represented with color coding such that state
transitions are clearly represented during parsing.

Matches on lines are highlighted to show extracted values and hovering
over a match shows the value and corresponding regex that was matched.
"""
from collections import namedtuple
from textwrap import dedent

import re

LINE_SATURATION = 40
LINE_LIGHTNESS = 60
MATCH_SATURATION = 100
MATCH_LIGHTNESS = 30


class LineHistory(namedtuple('LineHistory', ['line', 'state', 'matches', 'match_index_pairs'])):
  """" The match history for a given line when parsed using the FSM.

  Contains the regex match objects for that line,
  which are converted to indices for highlighting
  """


class MatchedPair(namedtuple('MatchPair', ['match_obj', 'rule'])):
  """" Stores the line history when parsed using the FSM."""


class StartStopIndex(namedtuple('StartStopIndex', ['start', 'end', 'value'])):
  """Represents the start and stop indices of a match for a given template value."""
  def __eq__(self, other):
    return self.start == other.start and self.end == other.end

  def __gt__(self, other):
    return self.start > other.start


class VisualDebugger(object):
  """Responsible for building the parse history of a TextFSM object into a visual html doc. """

  def __init__(self, fsm, cli_text):
    self.fsm = fsm
    self.cli_text = cli_text
    self.state_colormap = {}

  @staticmethod
  def add_prelude_boilerplate(html_file):
    prelude_lines = dedent('''
            <!DOCTYPE html>
              <html>
                <head>
                  <meta charset='UTF-8'>
                  <title>visual debugger</title>
            ''')

    html_file.write(prelude_lines)

  def build_state_colors(self):
    """Basic colour wheel selection for state highlighting"""
    cntr = 1
    for state_name in self.fsm.states.keys():
      self.state_colormap[state_name] = (67 * cntr) % 360
      cntr += 1

  @staticmethod
  def hsl_css(h, s, l):
    """Return the CSS string for HSL background color."""
    return "  background-color: hsl({},{}%,{}%);\n".format(h, s, l)

  def add_css_styling(self, html_file):
    css_prelude_lines = dedent('''
            <style type='text/css'>
            body {
              font-family: Arial, Helvetica, sans-serif;
              background-color: hsl(40, 1%, 25%);
              margin: 0;
              padding: 0;
            }
            h4 {
              font-family: Arial, Helvetica, sans-serif;
              color: white;
              margin-top: 0;
            }
            .regex {
                background-color: silver;
                border: 2px;
                border-style: solid;
                border-color: black;
                display: none;
                border-radius: 5px;
                padding: 0 10px;
            }
            .cli-title{
                padding-top: 100px;
            }
            .states{
                position: fixed;
                background-color: dimgray;
                width: 100%;
                padding: 10px;
                margin-top: 0;
                box-shadow: 0 3px 8px #000000;
            }
            ''')

    html_file.writelines(css_prelude_lines)

    # Build and write state styling CSS
    for state_name in self.fsm.states.keys():
      state_block = [
        ".{}{{\n".format(state_name),
        self.hsl_css(
          self.state_colormap[state_name],
          LINE_SATURATION,
          LINE_LIGHTNESS
        ),
        "  border-radius: 5px;\n",
        "  padding: 0 10px;\n",
        "}\n"
      ]
      html_file.writelines(state_block)

    # Build and write state match styling CSS
    new_parse_history = []
    l_count = 0
    for line in self.fsm.parse_history:

      match_index_pairs = []

      # Flatten match index structure
      for match in line.matches:
        for key in match.match_obj.groupdict().keys():
          match_index_pairs.append(
            StartStopIndex(
              match.match_obj.start(key),
              match.match_obj.end(key),
              key
            )
          )

      # Merge indexes that overlap due to multiple rule matches for a single line.
      self.merge_indexes(match_index_pairs)
      match_index_pairs.sort()

      # Overwrite named tuple data member
      line = line._replace(match_index_pairs=match_index_pairs)
      new_parse_history.append(line)

      # Generate CSS for match highlighting and on-hover regex display
      if line.match_index_pairs:
        match_count = 0
        for index_pair in line.match_index_pairs:
          match_block = [
            ".{}-match-{}-{}{{\n".format(line.state, l_count, match_count),
            self.hsl_css(
              self.state_colormap[line.state],
              MATCH_SATURATION,
              MATCH_LIGHTNESS
            ),
            "  border-radius: 5 px;\n",
            "  font-weight: bold;\n"
            "  color: white;\n",
            "  padding: 0 5px;\n",
            "}\n",
            ".{}-match-{}-{}:hover + .regex {{\n".format(line.state, l_count, match_count),
            "  display: inline;\n",
            "}\n"
          ]
          html_file.writelines(match_block)
          match_count += 1
      l_count += 1

    # Overwrite parse history from FSM with newly processed history
    self.fsm.parse_history = new_parse_history

    css_closing_lines = [
      "</style>\n"
    ]

    html_file.writelines(css_closing_lines)

  def merge_indexes(self, match_index_pairs):
    """Merge overlapping index pairs that may occur due to multiple rule matches."""

    def overlapping(index_a, index_b):
      if index_a.end > index_b.start and index_a.start < index_b.end:
        return True
      if index_a.start < index_b.end and index_b.start < index_a.end:
        return True
      if index_a.start < index_b.start and index_a.end > index_b.end:
        return True
      if index_b.start < index_a.start and index_b.end > index_a.end:
        return True

    def merge_pairs(index_a, index_b):
      start = 0
      if index_a.start < index_b.start:
        start = index_a.start
      else:
        start = index_b.start
      if index_a.end < index_b.end:
        end = index_b.end
      else:
        end = index_a.end
      return StartStopIndex(start, end, [index_a.value, index_b.value])

    for pair in match_index_pairs:
      overlap = False
      match_index_pairs.remove(pair)
      for check_pair in match_index_pairs:
        if overlapping(pair, check_pair):
          overlap = True
          match_index_pairs.remove(check_pair)
          match_index_pairs.append(merge_pairs(pair, check_pair))
          break
      if not overlap:
        match_index_pairs.append(pair)

  def add_cli_text(self, html_file):
    """Builds the HTML elements of the debug page including:
      - Colored States Header Bar
      - Highlighted CLI Text
    """

    cli_text_prelude = [
      "</head>\n",
      "<header class='states'>",
      "<h4>States:</h4>\n"
    ]

    for state in self.state_colormap.keys():
      cli_text_prelude += [
        "<button style='font-weight: bold;' class='{}'>{}</button>\n".format(state, state)
      ]

    cli_text_prelude += [
      "</header>\n",
      "<body>\n",
      "<h4 class='cli-title'>CLI Text:</h4>\n",
      "<pre>\n"
    ]

    html_file.writelines(cli_text_prelude)

    lines = self.cli_text.splitlines()
    lines = [line + '\n' for line in lines]

    # Process each line history and add highlighting where matches occur.
    l_count = 0
    for line_history in self.fsm.parse_history:
      # Only process highlights where matches occur.
      if line_history.match_index_pairs:
        built_line = ""
        prev_end = 0
        match_count = 0

        for index in line_history.match_index_pairs:
          if index.start < 0 or index.end < 0:
            continue

          # Strip out useless pattern format characters and value label.
          # Escape chevrons in regex pattern.
          re_patterns = []
          values = []
          if type(index.value) is list:
            values = index.value
            for v in index.value:
              value_pattern = self.fsm.value_map[v]
              re_patterns.append(re.sub('\?P<.*?>', '', value_pattern).replace('<', '&lt').replace('>', '&gt'))
          else:
            values.append(index.value)
            value_pattern = self.fsm.value_map[index.value]
            re_patterns.append(re.sub('\?P<.*?>', '', value_pattern).replace('<', '&lt').replace('>', '&gt'))

          # Build section of match and escape non HTML chevrons if present
          built_line += (
              lines[l_count][prev_end:index.start].replace('<', '&lt').replace('>', '&gt')
              + "<span class='{}-match-{}-{}'>".format(line_history.state, l_count, match_count)
              + lines[l_count][index.start:index.end].replace('<', '&lt').replace('>', '&gt')
              + "</span><span class='regex'>{} >> {}</span>".format(re_patterns, values)
          )
          prev_end = index.end
          match_count += 1

        built_line += lines[l_count][line_history.match_index_pairs[-1].end:].replace('<', '&lt').replace('>', '&gt')
        lines[l_count] = built_line
      else:
        # Escape non HTML tag chevrons if present
        lines[l_count] = lines[l_count].replace('<', '&lt').replace('>', '&gt')

      # Add final span wrapping tag for line state color
      lines[l_count] = ("<span class='{}'>".format(line_history.state)
                        + lines[l_count] + "</span>")
      l_count += 1

    # Close off document
    end_body_end_html = dedent('''
        </pre>
      </body>
    </html>
    ''')

    html_file.writelines(lines)

    html_file.write(end_body_end_html)

  def build_debug_html(self):
    """Calls HTML building procedures in sequence to create debug HTML doc."""
    with open("debug.html", "w+") as f:
      self.add_prelude_boilerplate(f)
      self.build_state_colors()
      self.add_css_styling(f)
      self.add_cli_text(f)
