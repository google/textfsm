from collections import namedtuple

LINE_SATURATION = 70
LINE_LIGHTNESS = 90
MATCH_SATURATION = 100
MATCH_LIGHTNESS = 50

BORDER_RADIUS = 5


class LineHistory(namedtuple('LineHistory', ['line', 'state', 'matches'])):
    pass


class MatchedPair(namedtuple('MatchPair', ['match_obj', 'rule'])):
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

        for line in self.fsm.parse_history:
            if line.matches:
                for matched in line.matches:
                    print(matched.rule.regex)

        css_closing_lines = [
            "</style>\n"
        ]

        html_file.writelines(css_closing_lines)

    def build_debug_html(self):
        with open("debug.html", "w+") as f:
            self.add_prelude_boilerplate(f)
            self.build_state_colors()
            self.add_css_styling(f)



