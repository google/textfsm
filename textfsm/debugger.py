from collections import namedtuple
from textwrap import dedent

import re

LINE_SATURATION = 40
LINE_LIGHTNESS = 60
MATCH_SATURATION = 100
MATCH_LIGHTNESS = 30

BORDER_RADIUS = 5


class LineHistory(namedtuple('LineHistory', ['line', 'state', 'matches', 'match_index_pairs'])):
  pass


class MatchedPair(namedtuple('MatchPair', ['match_obj', 'rule'])):
  pass


class StartStopIndex(namedtuple('StartStopIndex', ['start', 'end', 'value'])):

  def __eq__(self, other):
    return self.start == other.start and self.end == other.end

  def __gt__(self, other):
    return self.start > other.start


class VisualDebugger(object):

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
    cntr = 1
    for state_name in self.fsm.states.keys():
      self.state_colormap[state_name] = (67 * cntr) % 360
      cntr += 1

  @staticmethod
  def hsl_css(h, s, l):
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
        "  border-radius: {}px;\n".format(BORDER_RADIUS),
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

      self.merge_indexes(match_index_pairs)
      match_index_pairs.sort()
      line = line._replace(match_index_pairs=match_index_pairs)
      new_parse_history.append(line)
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
            "  border-radius: {}px;\n".format(BORDER_RADIUS),
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
    self.fsm.parse_history = new_parse_history

    css_closing_lines = [
      "</style>\n"
    ]

    html_file.writelines(css_closing_lines)

  def merge_indexes(self, match_index_pairs):

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

    l_count = 0
    for line_history in self.fsm.parse_history:
      if line_history.match_index_pairs:
        # Merge indexes if there is any overlap
        built_line = ""
        prev_end = 0
        match_count = 0
        for index in line_history.match_index_pairs:
          if index.start < 0 or index.end < 0:
            continue

          # Strip out useless pattern format characters
          value_pattern = self.fsm.value_map[index.value]
          regex = re.sub('\?P<.*?>', '', value_pattern).replace('<', '&lt').replace('>', '&gt')

          # Build section of match and escape HTML tag chevrons if present
          built_line += (
              lines[l_count][prev_end:index.start].replace('<', '&lt').replace('>', '&gt')
              + "<span class='{}-match-{}-{}'>".format(line_history.state, l_count, match_count)
              + lines[l_count][index.start:index.end].replace('<', '&lt').replace('>', '&gt')
              + "</span><span class='regex'>{} >> {}</span>".format(regex, index.value)
          )
          prev_end = index.end
          match_count += 1

        built_line += lines[l_count][line_history.match_index_pairs[-1].end:].replace('<', '&lt').replace('>', '&gt')
        lines[l_count] = built_line
      else:
        # Escape HTML tag chevrons if present
        lines[l_count] = lines[l_count].replace('<', '&lt').replace('>', '&gt')

      # Add final span wrapping tag for line state color
      lines[l_count] = ("<span class='{}'>".format(line_history.state)
                        + lines[l_count] + "</span>")
      l_count += 1

    # Close off document
    end_body_end_html = [
      "</pre>\n",
      "</body>\n",
      "</html>\n"
    ]

    html_file.writelines(lines)

    html_file.writelines(end_body_end_html)

  def build_debug_html(self):
    with open("debug.html", "w+") as f:
      self.add_prelude_boilerplate(f)
      self.build_state_colors()
      self.add_css_styling(f)
      self.add_cli_text(f)
