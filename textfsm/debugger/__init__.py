from collections import namedtuple

LINE_SATURATION = 40
LINE_LIGHTNESS = 60
MATCH_SATURATION = 100
MATCH_LIGHTNESS = 30

BORDER_RADIUS = 5


class LineHistory(namedtuple('LineHistory', ['line', 'state', 'matches'])):
    pass


class MatchedPair(namedtuple('MatchPair', ['match_obj', 'rule'])):
    pass


class StartStopIndex(namedtuple('StartStopIndex', ['start', 'end'])):

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
            "background-color: hsl(40, 1%, 25%)\n"
            "}\n",
            "h4 {\n",
            "font-family: Arial, Helvetica, sans-serif;\n",
            "color: white;\n",
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
                "padding: 0px 10px;\n",
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
            return StartStopIndex(start, end)

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
            "<body>",
            "<h4>States:</h4>\n"
        ]

        for state in self.state_colormap.keys():
            cli_text_prelude += [
                "<button class='{}'>{}</button>\n".format(state, state)
            ]

        cli_text_prelude += [
            "<h4>CLI Text:</h4>\n"
            "<pre>\n"
        ]

        html_file.writelines(cli_text_prelude)

        lines = self.cli_text.splitlines()
        lines = [line + '\n' for line in lines]

        l_count = 0
        for line_history in self.fsm.parse_history:

            match_index_pairs = []

            # Flatten match index structure
            for match in line_history.matches:
                if len(match.match_obj.groups()) > 0:
                    for i in range(1, len(match.match_obj.groups()) + 1):
                        match_index_pairs.append(
                            StartStopIndex(
                                match.match_obj.start(i),
                                match.match_obj.end(i)
                            )
                        )

            if match_index_pairs:
                # Merge indexes if there is any overlap
                self.merge_indexes(match_index_pairs)
                match_index_pairs.sort()
                built_line = ""
                prev_end = 0
                for index in match_index_pairs:
                    built_line += (
                          lines[l_count][prev_end:index.start]
                          + "<span class='{}-match'>".format(line_history.state)
                          + lines[l_count][index.start:index.end]
                          + "</span>"
                    )
                    prev_end = index.end

                built_line += lines[l_count][match_index_pairs[-1].end:]
                lines[l_count] = built_line

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



