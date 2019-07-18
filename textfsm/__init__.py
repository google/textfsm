"""Template based text parser.

This module implements a parser, intended to be used for converting
human readable text, such as command output from a router CLI, into
a list of records, containing values extracted from the input text.

A simple template language is used to describe a state machine to
parse a specific type of text input, returning a record of values
for each input entity.
"""
from textfsm.parser import *

__version__ = '1.1.0'
