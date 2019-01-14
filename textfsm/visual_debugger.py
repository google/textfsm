
class VisualDebugger:

    def __init__(self, fsm, parse_history):
        self.fsm = fsm
        self.parse_history = parse_history
        self.state_colormap = {}

    def add_prelude_boilerplate(self, html_file):
        prelude_lines = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<meta charset='UTF-8'>",
            "<title>visual debugger</title>"
        ]

        html_file.writelines(prelude_lines)

    def hsl_css(self, h, s, l):
        return "background-color: hsl({},{}%,{}%);".format(h, s, l)

    def add_css_styling(self, html_file):
        css_prelude_lines = [
            "<style type='text/css'>",
            "body {",
            "font-family: Arial, Helvetica, sans-serif;",
            "}",
        ]

        css_closing_lines = [
            "</style"
        ]

        html_file.writelines(css_prelude_lines)

        for state_name in self.fsm.states.keys():
            print(state_name)

    def build_debug_html(self):
        with open("debug.html", "w+") as f:
            self.add_prelude_boilerplate(f)
            self.add_css_styling(f)


class ParseHistory:

    def __init__(self):
         self.line_histories = []

    class LineHistory:

        def __init__(self, state, line_string):
            self.state = state
            self.line_string = line_string
            self.rule_matches = []

        def add_rule_match(self, rule, match):
            self.rule_matches.append((rule, match))




