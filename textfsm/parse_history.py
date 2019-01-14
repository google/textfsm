class LineHistory(object):

    def __init__(self, line, state_name):
        self.line_string = line
        self.state_name = state_name
        self.matched_rules = []
    

class ParseHistory(object):

    def __init__(self):
        self.line_histories = []
        
    def add_line_history(self, line, state_name):
        self.line_histories.append(LineHistory(line, state_name))

    def get_states(self):
        return [line.state_name for line in self.line_histories]


class MatchPair(object):

    def __init__(self, match, rule):
        self.match = match
        self.rule = rule

    
