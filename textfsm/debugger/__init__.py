from collections import namedtuple


class LineHistory(namedtuple('LineHistory', ['line', 'state', 'matches'])):
    pass


class MatchedPair(namedtuple('MatchPair', ['match_obj', 'rule'])):
    pass
