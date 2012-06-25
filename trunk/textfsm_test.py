#!/usr/bin/python2.4
#
# Copyright 2010 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.

"""Unittest for textfsm module."""


import cStringIO
import unittest
# http://python-mock.sourceforge.net/

import textfsm


class UnitTestFSM(unittest.TestCase):
  """Tests the FSM engine."""

  def testFSMValue(self):
    # Check basic line is parsed.
    line = 'Value beer (\S+)'
    v = textfsm.TextFSMValue()
    v.Parse(line)
    self.failUnlessEqual(v.name, 'beer')
    self.failUnlessEqual(v.regex, '(\S+)')
    self.failUnlessEqual(v.template, '(?P<beer>\S+)')
    self.failIf(v.options)

    # Test options
    line = 'Value Filldown,Required beer (\S+)'
    v = textfsm.TextFSMValue(options_class=textfsm.TextFSMOptions)
    v.Parse(line)
    self.failUnlessEqual(v.name, 'beer')
    self.failUnlessEqual(v.regex, '(\S+)')
    self.failUnlessEqual(v.OptionNames(), ['Filldown', 'Required'])

    # Multiple parenthesis.
    v = textfsm.TextFSMValue(options_class=textfsm.TextFSMOptions)
    v.Parse('Value Required beer (boo(hoo))')
    self.failUnlessEqual(v.name, 'beer')
    self.failUnlessEqual(v.regex, '(boo(hoo))')
    self.failUnlessEqual(v.template, '(?P<beer>boo(hoo))')
    self.failUnlessEqual(v.OptionNames(), ['Required'])

    # regex must be bounded by parenthesis.
    self.failUnlessRaises(textfsm.TextFSMTemplateError,
                          v.Parse,
                          'Value beer (boo(hoo)))boo')
    self.failUnlessRaises(textfsm.TextFSMTemplateError,
                          v.Parse,
                          'Value beer boo(boo(hoo)))')
    self.failUnlessRaises(textfsm.TextFSMTemplateError,
                          v.Parse,
                          'Value beer (boo)hoo)')

    # String function.
    v = textfsm.TextFSMValue(options_class=textfsm.TextFSMOptions)
    v.Parse('Value Required beer (boo(hoo))')
    self.failUnlessEqual(str(v), 'Value Required beer (boo(hoo))')
    v = textfsm.TextFSMValue(options_class=textfsm.TextFSMOptions)
    v.Parse(
        'Value Required,Filldown beer (bo\S+(hoo))')
    self.failUnlessEqual(str(v), 'Value Required,Filldown beer (bo\S+(hoo))')

  def testFSMRule(self):

    # Basic line, no action
    line = '  ^A beer called ${beer}'
    r = textfsm.TextFSMRule(line)
    self.failUnlessEqual(r.match, '^A beer called ${beer}')
    self.failUnlessEqual(r.line_op, '')
    self.failUnlessEqual(r.new_state, '')
    self.failUnlessEqual(r.record_op, '')
    # Multiple matches
    line = '  ^A $hi called ${beer}'
    r = textfsm.TextFSMRule(line)
    self.failUnlessEqual(r.match, '^A $hi called ${beer}')
    self.failUnlessEqual(r.line_op, '')
    self.failUnlessEqual(r.new_state, '')
    self.failUnlessEqual(r.record_op, '')

    # Line with action.
    line = '  ^A beer called ${beer} -> Next'
    r = textfsm.TextFSMRule(line)
    self.failUnlessEqual(r.match, '^A beer called ${beer}')
    self.failUnlessEqual(r.line_op, 'Next')
    self.failUnlessEqual(r.new_state, '')
    self.failUnlessEqual(r.record_op, '')
    # Line with record.
    line = '  ^A beer called ${beer} -> Continue.Record'
    r = textfsm.TextFSMRule(line)
    self.failUnlessEqual(r.match, '^A beer called ${beer}')
    self.failUnlessEqual(r.line_op, 'Continue')
    self.failUnlessEqual(r.new_state, '')
    self.failUnlessEqual(r.record_op, 'Record')
    # Line with new state.
    line = '  ^A beer called ${beer} -> Next.NoRecord End'
    r = textfsm.TextFSMRule(line)
    self.failUnlessEqual(r.match, '^A beer called ${beer}')
    self.failUnlessEqual(r.line_op, 'Next')
    self.failUnlessEqual(r.new_state, 'End')
    self.failUnlessEqual(r.record_op, 'NoRecord')

    # Bad syntax tests.
    self.failUnlessRaises(textfsm.TextFSMTemplateError, textfsm.TextFSMRule,
                          '  ^A beer called ${beer} -> Next Next Next')
    self.failUnlessRaises(textfsm.TextFSMTemplateError, textfsm.TextFSMRule,
                          '  ^A beer called ${beer} -> Boo.hoo')
    self.failUnlessRaises(textfsm.TextFSMTemplateError, textfsm.TextFSMRule,
                          '  ^A beer called ${beer} -> Continue.Record $Hi')

  def testImplicitDefaultRules(self):

    for line in ('  ^A beer called ${beer} -> Record End',
                 '  ^A beer called ${beer} -> End',
                 '  ^A beer called ${beer} -> Next.NoRecord End',
                 '  ^A beer called ${beer} -> Clear End',
                 '  ^A beer called ${beer} -> Error "Hello World"'):
      r = textfsm.TextFSMRule(line)
      self.failUnlessEqual(str(r), line)

    for line in ('  ^A beer called ${beer} -> Next "Hello World"',
                 '  ^A beer called ${beer} -> Record.Next',
                 '  ^A beer called ${beer} -> Continue End',
                 '  ^A beer called ${beer} -> Beer End'):
      self.failUnlessRaises(textfsm.TextFSMTemplateError,
                            textfsm.TextFSMRule, line)

  def testSpacesAroundAction(self):
    for line in ('  ^Hello World -> Boo',
                 '  ^Hello World ->  Boo',
                 '  ^Hello World ->   Boo'):
      self.failUnlessEqual(
          str(textfsm.TextFSMRule(line)), '  ^Hello World -> Boo')

    # A '->' without a leading space is considered part of the matching line.
    self.failUnlessEqual('  A simple line-> Boo -> Next',
                         str(textfsm.TextFSMRule(
                             '  A simple line-> Boo -> Next')))

  def testParseFSMVariables(self):
    # Trivial template to initiate object.
    f = cStringIO.StringIO('Value unused (.)\n\nStart\n')
    t = textfsm.TextFSM(f)

    # Trivial entry
    buf = 'Value Filldown Beer (beer)\n\n'
    f = cStringIO.StringIO(buf)
    t._ParseFSMVariables(f)

    # Single variable with commented header.
    buf = '# Headline\nValue Filldown Beer (beer)\n\n'
    f = cStringIO.StringIO(buf)
    t._ParseFSMVariables(f)
    self.failUnlessEqual(str(t._GetValue('Beer')), 'Value Filldown Beer (beer)')

    # Multiple variables.
    buf = ('# Headline\n'
           'Value Filldown Beer (beer)\n'
           'Value Required Spirits (whiskey)\n'
           'Value Filldown Wine (claret)\n'
           '\n')
    t._line_num = 0
    f = cStringIO.StringIO(buf)
    t._ParseFSMVariables(f)
    self.failUnlessEqual(str(t._GetValue('Beer')), 'Value Filldown Beer (beer)')
    self.failUnlessEqual(
        str(t._GetValue('Spirits')), 'Value Required Spirits (whiskey)')
    self.failUnlessEqual(str(t._GetValue('Wine')),
                         'Value Filldown Wine (claret)')

    # Multiple variables.
    buf = ('# Headline\n'
           'Value Filldown Beer (beer)\n'
           ' # A comment\n'
           'Value Spirits ()\n'
           'Value Filldown,Required Wine ((c|C)laret)\n'
           '\n')

    f = cStringIO.StringIO(buf)
    t._ParseFSMVariables(f)
    self.failUnlessEqual(str(t._GetValue('Beer')), 'Value Filldown Beer (beer)')
    self.failUnlessEqual(
        str(t._GetValue('Spirits')), 'Value Spirits ()')
    self.failUnlessEqual(str(t._GetValue('Wine')),
                         'Value Filldown,Required Wine ((c|C)laret)')

    # Malformed variables.
    buf = 'Value Beer (beer) beer'
    f = cStringIO.StringIO(buf)
    self.failUnlessRaises(textfsm.TextFSMTemplateError, t._ParseFSMVariables, f)

    buf = 'Value Filldown, Required Spirits ()'
    f = cStringIO.StringIO(buf)
    self.failUnlessRaises(textfsm.TextFSMTemplateError, t._ParseFSMVariables, f)
    buf = 'Value filldown,Required Wine ((c|C)laret)'
    f = cStringIO.StringIO(buf)
    self.failUnlessRaises(textfsm.TextFSMTemplateError, t._ParseFSMVariables, f)

    # Values that look bad but are OK.
    buf = ('# Headline\n'
           'Value Filldown Beer (bee(r), (and) (M)ead$)\n'
           '# A comment\n'
           'Value Spirits,and,some ()\n'
           'Value Filldown,Required Wine ((c|C)laret)\n'
           '\n')
    f = cStringIO.StringIO(buf)
    t._ParseFSMVariables(f)
    self.failUnlessEqual(str(t._GetValue('Beer')),
                         'Value Filldown Beer (bee(r), (and) (M)ead$)')
    self.failUnlessEqual(
        str(t._GetValue('Spirits,and,some')), 'Value Spirits,and,some ()')
    self.failUnlessEqual(str(t._GetValue('Wine')),
                         'Value Filldown,Required Wine ((c|C)laret)')

    # Variable name too long.
    buf = ('Value Filldown '
           'nametoolong_nametoolong_nametoolo_nametoolong_nametoolong '
           '(beer)\n\n')
    f = cStringIO.StringIO(buf)
    self.failUnlessRaises(textfsm.TextFSMTemplateError,
                          t._ParseFSMVariables, f)

  def testParseFSMState(self):

    f = cStringIO.StringIO('Value Beer (.)\nValue Wine (\w)\n\nStart\n')
    t = textfsm.TextFSM(f)

    # Fails as we already have 'Start' state.
    buf = 'Start\n  ^.\n'
    f = cStringIO.StringIO(buf)
    self.failUnlessRaises(textfsm.TextFSMTemplateError, t._ParseFSMState, f)

    # Remove start so we can test new Start state.
    t.states = {}

    # Single state.
    buf = '# Headline\nStart\n  ^.\n\n'
    f = cStringIO.StringIO(buf)
    t._ParseFSMState(f)
    self.failUnless(t.states['Start'])
    self.failUnlessEqual(str(t.states['Start'][0]), '  ^.')
    try:
      _ = t.states['Start'][1]
    except IndexError:
      pass

    # Multiple states.
    buf = '# Headline\nStart\n  ^.\n  ^Hello World\n  ^Last-[Cc]ha$$nge\n'
    f = cStringIO.StringIO(buf)
    t._line_num = 0
    t.states = {}
    t._ParseFSMState(f)
    self.failUnlessEqual(str(t.states['Start'][0]), '  ^.')
    self.failUnlessEqual(str(t.states['Start'][1]), '  ^Hello World')
    self.failUnlessEqual(t.states['Start'][1].line_num, 4)
    self.failUnlessEqual(str(t.states['Start'][2]), '  ^Last-[Cc]ha$$nge')
    try:
      _ = t.states['Start'][3]
    except IndexError:
      pass

    t.states = {}
    # Malformed states.
    buf = 'St%art\n  ^.\n  ^Hello World\n'
    f = cStringIO.StringIO(buf)
    self.failUnlessRaises(textfsm.TextFSMTemplateError, t._ParseFSMState, f)

    buf = 'Start\n^.\n  ^Hello World\n'
    f = cStringIO.StringIO(buf)
    self.failUnlessRaises(textfsm.TextFSMTemplateError, t._ParseFSMState, f)

    buf = '  Start\n  ^.\n  ^Hello World\n'
    f = cStringIO.StringIO(buf)
    self.failUnlessRaises(textfsm.TextFSMTemplateError, t._ParseFSMState, f)

    # Multiple variables and substitution (depends on _ParseFSMVariables).
    buf = ('# Headline\nStart\n  ^.${Beer}${Wine}.\n'
           '  ^Hello $Beer\n  ^Last-[Cc]ha$$nge\n')
    f = cStringIO.StringIO(buf)
    t.states = {}
    t._ParseFSMState(f)
    self.failUnlessEqual(str(t.states['Start'][0]),
                         '  ^.${Beer}${Wine}.')
    self.failUnlessEqual(str(t.states['Start'][1]), '  ^Hello $Beer')
    self.failUnlessEqual(str(t.states['Start'][2]), '  ^Last-[Cc]ha$$nge')
    try:
      _ = t.states['Start'][3]
    except IndexError:
      pass

    t.states['bogus'] = []

    # State name too long (>32 char).
    buf = 'nametoolong_nametoolong_nametoolong_nametoolong_nametoolo\n  ^.\n\n'
    f = cStringIO.StringIO(buf)
    self.failUnlessRaises(textfsm.TextFSMTemplateError, t._ParseFSMState, f)

  def testInvalidStates(self):

    # 'Continue' should not accept a destination.
    self.failUnlessRaises(textfsm.TextFSMTemplateError, textfsm.TextFSMRule,
                          '^.* -> Continue Start')

    # 'Error' accepts a text string but "next' state does not.
    self.failUnlessEqual(str(textfsm.TextFSMRule('  ^ -> Error "hi there"')),
                         '  ^ -> Error "hi there"')
    self.failUnlessRaises(textfsm.TextFSMTemplateError, textfsm.TextFSMRule,
                          '^.* -> Next "Hello World"')

  def testRuleStartsWithCarrot(self):

    f = cStringIO.StringIO(
        'Value Beer (.)\nValue Wine (\w)\n\nStart\n  A Simple line')
    self.failUnlessRaises(textfsm.TextFSMTemplateError, textfsm.TextFSM, f)

  def testValidateFSM(self):

    # No Values.
    f = cStringIO.StringIO('\nNotStart\n')
    self.failUnlessRaises(textfsm.TextFSMTemplateError, textfsm.TextFSM, f)

    # No states.
    f = cStringIO.StringIO('Value unused (.)\n\n')
    self.failUnlessRaises(textfsm.TextFSMTemplateError, textfsm.TextFSM, f)

    # No 'Start' state.
    f = cStringIO.StringIO('Value unused (.)\n\nNotStart\n')
    self.failUnlessRaises(textfsm.TextFSMTemplateError, textfsm.TextFSM, f)

    # Has 'Start' state with valid destination
    f = cStringIO.StringIO('Value unused (.)\n\nStart\n')
    t = textfsm.TextFSM(f)
    t.states['Start'] = []
    t.states['Start'].append(textfsm.TextFSMRule('^.* -> Start'))
    t._ValidateFSM()

    # Invalid destination.
    t.states['Start'].append(textfsm.TextFSMRule('^.* -> bogus'))
    self.failUnlessRaises(textfsm.TextFSMTemplateError, t._ValidateFSM)

    # Now valid again.
    t.states['bogus'] = []
    t.states['bogus'].append(textfsm.TextFSMRule('^.* -> Start'))
    t._ValidateFSM()

    # Valid destination with options.
    t.states['bogus'] = []
    t.states['bogus'].append(textfsm.TextFSMRule('^.* -> Next.Record Start'))
    t._ValidateFSM()

    # Error with and without messages string.
    t.states['bogus'] = []
    t.states['bogus'].append(textfsm.TextFSMRule('^.* -> Error'))
    t._ValidateFSM()
    t.states['bogus'].append(textfsm.TextFSMRule('^.* -> Error "Boo hoo"'))
    t._ValidateFSM()

  def testTextFSM(self):

    # Trivial template
    buf = 'Value Beer (.*)\n\nStart\n  ^\w\n'
    buf_result = buf
    f = cStringIO.StringIO(buf)
    t = textfsm.TextFSM(f)
    self.failUnlessEqual(str(t), buf_result)

    # Slightly more complex, multple vars.
    buf = 'Value A (.*)\nValue B (.*)\n\nStart\n  ^\w\n\nState1\n  ^.\n'
    buf_result = buf
    f = cStringIO.StringIO(buf)
    t = textfsm.TextFSM(f)
    self.failUnlessEqual(str(t), buf_result)

    # Complex template, multiple vars and states with comments (no var options).
    buf = """# Header
# Header 2
Value Beer (.*)
Value Wine (\w+)

# An explanation.
Start
  ^hi there ${Wine}. -> Next.Record State1

State1
  ^\w
  ^$Beer .. -> Start
  # Some comments
  ^$$ -> Next
  ^$$ -> End

End
# Tail comment.
"""

    buf_result = """Value Beer (.*)
Value Wine (\w+)

Start
  ^hi there ${Wine}. -> Next.Record State1

State1
  ^\w
  ^$Beer .. -> Start
  ^$$ -> Next
  ^$$ -> End
"""
    f = cStringIO.StringIO(buf)
    t = textfsm.TextFSM(f)
    self.failUnlessEqual(str(t), buf_result)

  def testParseText(self):

    # Trivial FSM, no records produced.
    tplt = 'Value unused (.)\n\nStart\n  ^Trivial SFM\n'
    t = textfsm.TextFSM(cStringIO.StringIO(tplt))

    data = 'Non-matching text\nline1\nline 2\n'
    self.failIf(t.ParseText(data))
    # Matching.
    data = 'Matching text\nTrivial SFM\nline 2\n'
    self.failIf(t.ParseText(data))

    # Simple FSM, One Variable no options.
    tplt = 'Value boo (.*)\n\nStart\n  ^$boo -> Next.Record\n\nEOF\n'
    t = textfsm.TextFSM(cStringIO.StringIO(tplt))

    # Matching one line.
    # Tests 'Next' & 'Record' actions.
    data = 'Matching text'
    result = t.ParseText(data)
    self.failUnlessEqual(str(result), "[['Matching text']]")

    # Matching two lines. Reseting FSM before Parsing.
    t.Reset()
    data = 'Matching text\nAnd again'
    result = t.ParseText(data)
    self.failUnlessEqual(str(result),
                         "[['Matching text'], ['And again']]")

    # Two Variables and singular options.
    tplt = ('Value Required boo (one)\nValue Filldown hoo (two)\n\n'
            'Start\n  ^$boo -> Next.Record\n  ^$hoo -> Next.Record\n\n'
            'EOF\n')
    t = textfsm.TextFSM(cStringIO.StringIO(tplt))

    # Matching two lines. Only one records returned due to 'Required' flag.
    # Tests 'Filldown' and 'Required' options.
    data = 'two\none'
    result = t.ParseText(data)
    self.failUnlessEqual(str(result), "[['one', 'two']]")

    t = textfsm.TextFSM(cStringIO.StringIO(tplt))
    # Matching two lines. Two records returned due to 'Filldown' flag.
    data = 'two\none\none'
    t.Reset()
    result = t.ParseText(data)
    self.failUnlessEqual(
        str(result), "[['one', 'two'], ['one', 'two']]")

    # Multiple Variables and options.
    tplt = ('Value Required,Filldown boo (one)\n'
            'Value Filldown,Required hoo (two)\n\n'
            'Start\n  ^$boo -> Next.Record\n  ^$hoo -> Next.Record\n\n'
            'EOF\n')
    t = textfsm.TextFSM(cStringIO.StringIO(tplt))
    data = 'two\none\none'
    result = t.ParseText(data)
    self.failUnlessEqual(
        str(result), "[['one', 'two'], ['one', 'two']]")

  def testParseNullText(self):

    # Simple FSM, One Variable no options.
    tplt = 'Value boo (.*)\n\nStart\n  ^$boo -> Next.Record\n\n'
    t = textfsm.TextFSM(cStringIO.StringIO(tplt))

    # Null string
    data = ''
    result = t.ParseText(data)
    self.failUnlessEqual(result, [])

  def testReset(self):

    tplt = 'Value boo (.*)\n\nStart\n  ^$boo -> Next.Record\n\nEOF\n'
    t = textfsm.TextFSM(cStringIO.StringIO(tplt))
    data = 'Matching text'
    result1 = t.ParseText(data)
    t.Reset()
    result2 = t.ParseText(data)
    self.failUnlessEqual(str(result1), str(result2))

    tplt = ('Value boo (one)\nValue hoo (two)\n\n'
            'Start\n  ^$boo -> State1\n\n'
            'State1\n  ^$hoo -> Start\n\n'
            'EOF')
    t = textfsm.TextFSM(cStringIO.StringIO(tplt))

    data = 'one'
    t.ParseText(data)
    t.Reset()
    self.failUnlessEqual(t._cur_state[0].match, '^$boo')
    self.failUnlessEqual(t._GetValue('boo').value, None)
    self.failUnlessEqual(t._GetValue('hoo').value, None)
    self.failUnlessEqual(t._result, [])

  def testClear(self):

    # Clear Filldown variable.
    # Tests 'Clear'.
    tplt = ('Value Required boo (on.)\n'
            'Value Filldown,Required hoo (tw.)\n\n'
            'Start\n  ^$boo -> Next.Record\n  ^$hoo -> Next.Clear')

    t = textfsm.TextFSM(cStringIO.StringIO(tplt))
    data = 'one\ntwo\nonE\ntwO'
    result = t.ParseText(data)
    self.failUnlessEqual(
        str(result), ("[['onE', 'two']]"))

    # Clearall, with Filldown variable.
    # Tests 'Clearall'.
    tplt = ('Value Filldown boo (on.)\n'
            'Value Filldown hoo (tw.)\n\n'
            'Start\n  ^$boo -> Next.Clearall\n'
            '  ^$hoo')

    t = textfsm.TextFSM(cStringIO.StringIO(tplt))
    data = 'one\ntwo'
    result = t.ParseText(data)
    self.failUnlessEqual(
        str(result), ("[['', 'two']]"))

  def testContinue(self):

    tplt = ('Value Required boo (on.)\n'
            'Value Filldown,Required hoo (on.)\n\n'
            'Start\n  ^$boo -> Continue\n  ^$hoo -> Continue.Record')

    t = textfsm.TextFSM(cStringIO.StringIO(tplt))
    data = 'one\non0'
    result = t.ParseText(data)
    self.failUnlessEqual(
        str(result), ("[['one', 'one'], ['on0', 'on0']]"))

  def testError(self):

    tplt = ('Value Required boo (on.)\n'
            'Value Filldown,Required hoo (on.)\n\n'
            'Start\n  ^$boo -> Continue\n  ^$hoo -> Error')

    t = textfsm.TextFSM(cStringIO.StringIO(tplt))
    data = 'one'
    self.failUnlessRaises(textfsm.TextFSMError, t.ParseText, data)

    tplt = ('Value Required boo (on.)\n'
            'Value Filldown,Required hoo (on.)\n\n'
            'Start\n  ^$boo -> Continue\n  ^$hoo -> Error "Hello World"')

    t = textfsm.TextFSM(cStringIO.StringIO(tplt))
    self.failUnlessRaises(textfsm.TextFSMError, t.ParseText, data)

  def testKey(self):
    tplt = ('Value Required boo (on.)\n'
            'Value Required,Key hoo (on.)\n\n'
            'Start\n  ^$boo -> Continue\n  ^$hoo -> Record')

    t = textfsm.TextFSM(cStringIO.StringIO(tplt))
    self.failUnless('Key' in t._GetValue('hoo').OptionNames())
    self.failUnless('Key' not in t._GetValue('boo').OptionNames())

  def testList(self):

    tplt = ('Value List boo (on.)\n'
            'Value hoo (tw.)\n\n'
            'Start\n  ^$boo\n  ^$hoo -> Next.Record\n\n'
            'EOF')

    t = textfsm.TextFSM(cStringIO.StringIO(tplt))
    data = 'one\ntwo\non0\ntw0'
    result = t.ParseText(data)
    self.failUnlessEqual(
        str(result), ("[[['one'], 'two'], "
                      "[['on0'], 'tw0']]"))

    tplt = ('Value List,Filldown boo (on.)\n'
            'Value hoo (on.)\n\n'
            'Start\n  ^$boo -> Continue\n  ^$hoo -> Next.Record\n\n'
            'EOF')

    t = textfsm.TextFSM(cStringIO.StringIO(tplt))
    data = 'one\non0\non1'
    result = t.ParseText(data)
    self.failUnlessEqual(
        str(result), ("[[['one'], 'one'], "
                      "[['one', 'on0'], 'on0'], "
                      "[['one', 'on0', 'on1'], 'on1']]"))

    tplt = ('Value List,Required boo (on.)\n'
            'Value hoo (tw.)\n\n'
            'Start\n  ^$boo -> Continue\n  ^$hoo -> Next.Record\n\n'
            'EOF')

    t = textfsm.TextFSM(cStringIO.StringIO(tplt))
    data = 'one\ntwo\ntw2'
    result = t.ParseText(data)
    self.failUnlessEqual(str(result), ("[[['one'], 'two']]"))

  def testGetValuesByAttrib(self):

    tplt = ('Value Required boo (on.)\n'
            'Value Required,List hoo (on.)\n\n'
            'Start\n  ^$boo -> Continue\n  ^$hoo -> Record')

    # Explicit default.
    t = textfsm.TextFSM(cStringIO.StringIO(tplt))
    self.failUnlessEqual(t.GetValuesByAttrib('List'), ['hoo'])
    self.failUnlessEqual(t.GetValuesByAttrib('Filldown'), [])
    result = t.GetValuesByAttrib('Required')
    result.sort()
    self.assertEqual(result, ['boo', 'hoo'])

  def testStateChange(self):

    # Sinple state change, no actions
    tplt = ('Value boo (one)\nValue hoo (two)\n\n'
            'Start\n  ^$boo -> State1\n\nState1\n  ^$hoo -> Start\n\n'
            'EOF')
    t = textfsm.TextFSM(cStringIO.StringIO(tplt))

    data = 'one'
    t.ParseText(data)
    self.failUnlessEqual(t._cur_state[0].match, '^$hoo')
    self.failUnlessEqual('one', t._GetValue('boo').value)
    self.failUnlessEqual(None, t._GetValue('hoo').value)
    self.failUnlessEqual(t._result, [])

    # State change with actions.
    tplt = ('Value boo (one)\nValue hoo (two)\n\n'
            'Start\n  ^$boo -> Next.Record State1\n\n'
            'State1\n  ^$hoo -> Start\n\n'
            'EOF')
    t = textfsm.TextFSM(cStringIO.StringIO(tplt))

    data = 'one'
    t.ParseText(data)
    self.failUnlessEqual(t._cur_state[0].match, '^$hoo')
    self.failUnlessEqual(None, t._GetValue('boo').value)
    self.failUnlessEqual(None, t._GetValue('hoo').value)
    self.failUnlessEqual(t._result, [['one', '']])

  def testEOF(self):

    # Implicit EOF.
    tplt = 'Value boo (.*)\n\nStart\n  ^$boo -> Next\n'
    t = textfsm.TextFSM(cStringIO.StringIO(tplt))

    data = 'Matching text'
    result = t.ParseText(data)
    self.failUnlessEqual(str(result), "[['Matching text']]")

    # EOF explicitly suppressed in template.
    tplt = 'Value boo (.*)\n\nStart\n  ^$boo -> Next\n\nEOF\n'
    t = textfsm.TextFSM(cStringIO.StringIO(tplt))

    result = t.ParseText(data)
    self.failUnlessEqual(str(result), '[]')

    # Implicit EOF suppressed by argument.
    tplt = 'Value boo (.*)\n\nStart\n  ^$boo -> Next\n'
    t = textfsm.TextFSM(cStringIO.StringIO(tplt))

    result = t.ParseText(data, eof=False)
    self.failUnlessEqual(str(result), '[]')

  def testEnd(self):

    # End State, EOF is skipped.
    tplt = 'Value boo (.*)\n\nStart\n  ^$boo -> End\n  ^$boo -> Record\n'
    t = textfsm.TextFSM(cStringIO.StringIO(tplt))
    data = 'Matching text A\nMatching text B'

    result = t.ParseText(data)
    self.failUnlessEqual(str(result), "[]")

    # End State, with explicit Record.
    tplt = 'Value boo (.*)\n\nStart\n  ^$boo -> Record End\n'
    t = textfsm.TextFSM(cStringIO.StringIO(tplt))

    result = t.ParseText(data)
    self.failUnlessEqual(str(result), "[['Matching text A']]")

    # EOF state transition is followed by implicit End State.
    tplt = 'Value boo (.*)\n\nStart\n  ^$boo -> EOF\n  ^$boo -> Record\n'
    t = textfsm.TextFSM(cStringIO.StringIO(tplt))

    result = t.ParseText(data)
    self.failUnlessEqual(str(result), "[['Matching text A']]")


  def testInvalidRegexp(self):

    tplt = 'Value boo (.$*)\n\nStart\n  ^$boo -> Next\n'
    self.failUnlessRaises(textfsm.TextFSMTemplateError,
                          textfsm.TextFSM, cStringIO.StringIO(tplt))

  def testValidRegexp(self):
    """RegexObjects uncopyable in Python 2.6."""

    tplt = 'Value boo (fo*)\n\nStart\n  ^$boo -> Record\n'
    t = textfsm.TextFSM(cStringIO.StringIO(tplt))
    data = 'f\nfo\nfoo\n'
    result = t.ParseText(data)
    self.failUnlessEqual(str(result), "[['f'], ['fo'], ['foo']]")

  def testReEnteringState(sefl):
    """Issue 2. TextFSM should leave file pointer at top of template file."""

    tplt = 'Value boo (.*)\n\nStart\n  ^$boo -> Next Stop\n\nStop\n  ^abc\n'
    output_text = 'one\ntwo'
    tmpl_file = cStringIO.StringIO(tplt)

    t = textfsm.TextFSM(tmpl_file)
    t.ParseText(output_text)
    t = textfsm.TextFSM(tmpl_file)
    t.ParseText(output_text)

  def testFillup(self):
    """Fillup should work ok."""
    tplt = """Value Required Col1 ([^-]+)
Value Fillup Col2 ([^-]+)
Value Fillup Col3 ([^-]+)

Start
  ^$Col1 -- -- -> Record
  ^$Col1 $Col2 -- -> Record
  ^$Col1 -- $Col3 -> Record
  ^$Col1 $Col2 $Col3 -> Record
"""
    data = """
1 -- B1
2 A2 --
3 -- B3
"""
    t = textfsm.TextFSM(cStringIO.StringIO(tplt))
    result = t.ParseText(data)
    self.failUnlessEqual(
        "[['1', 'A2', 'B1'], ['2', 'A2', 'B3'], ['3', '', 'B3']]",
        str(result))


if __name__ == '__main__':
  unittest.main()
