from collections import namedtuple

LINE_SATURATION = 70
LINE_LIGHTNESS = 75
MATCH_SATURATION = 100
MATCH_LIGHTNESS = 30

BORDER_RADIUS = 5


class LineHistory(namedtuple('LineHistory', ['line', 'state', 'matches'])):
    pass


class MatchedPair(namedtuple('MatchPair', ['match_obj', 'rule'])):
    pass


class StartStopIndex(namedtuple('StartStopIndex', ['start', 'stop'])):
    pass


class VisualDebugger(object):

    def __init__(self, fsm, cli_text):
        self.fsm = fsm
        self.cli_text = cli_text
        self.state_colormap = {}

    @staticmethod
    def add_prelude_boilerplate(html_file):
        prelude_lines = [
            "<!DOCTYPE html>\n",
            "<html>\n",
            "<head>\n",
            "<meta charset='UTF-8'>\n",
            "<title>visual debugger</title>\n"
        ]

        html_file.writelines(prelude_lines)

    def build_state_colors(self):
        h = 0
        separation = 30
        used_colors = set()
        for state_name in self.fsm.states.keys():
            while h in used_colors:
                h = (h + separation) % 360
            self.state_colormap[state_name] = h
            used_colors.add(h)
            h = (h + separation) % 360
            if h == 0:
                separation -= 10
                if separation == 0:
                    separation = 30

    @staticmethod
    def hsl_css(h, s, l):
        return "background-color: hsl({},{}%,{}%);\n".format(h, s, l)

    def add_css_styling(self, html_file):
        css_prelude_lines = [
            "<style type='text/css'>\n",
            "body {\n",
            "font-family: Arial, Helvetica, sans-serif;\n",
            "}\n",
        ]

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
                "border-radius: {}px;\n".format(BORDER_RADIUS),
                "}\n"
            ]
            html_file.writelines(state_block)

        # Build and write state match styling CSS
        state_matches = set()
        for line in self.fsm.parse_history:
            if line.matches:
                if line.state not in state_matches:
                    match_block = [
                        ".{}-match{{\n".format(line.state),
                        self.hsl_css(
                            self.state_colormap[line.state],
                            MATCH_SATURATION,
                            MATCH_LIGHTNESS
                        ),
                        "border-radius: {}px;\n".format(BORDER_RADIUS),
                        "font - weight: bold;\n"
                        "color: white;\n",
                        "}\n"
                    ]
                    state_matches.add(line.state)
                    html_file.writelines(match_block)

        css_closing_lines = [
            "</style>\n"
        ]

        html_file.writelines(css_closing_lines)

    def add_cli_text(self, html_file):

        end_head_start_body = [
            "</head>\n",
            "<body>\n",
            "<pre>\n"
        ]

        html_file.writelines(end_head_start_body)

        lines = self.cli_text.splitlines()
        lines = [line + '\n' for line in lines]

        l_count = 0
        for line_history in self.fsm.parse_history:

            match_index_pairs = []
            for match in line_history.matches:
                if len(match.match_obj.groups()) > 0:
                    built_line = lines[l_count][:match.match_obj.start(1)]
                    for i in range(0, len(match.match_obj.groups())):
                        built_line += (
                            "<span class='{}-match'>".format(line_history.state)
                            + lines[l_count][match.match_obj.start(i):match.match_obj.end(i)]
                            + "</span>"

                        )
                    built_line += lines[l_count][match.match_obj.end(1):]
                    lines[l_count] = built_line
                else:
                    print("ZERO")
                    print(match.match_obj.groups())

            lines[l_count] = ("<span class='{}'>".format(line_history.state)
                              + lines[l_count] + "</span>")
            l_count += 1



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



