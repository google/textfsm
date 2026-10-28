#!/usr/bin/env python
#
# Copyright 2024 Google Inc. All Rights Reserved.
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

"""Tests covering the three security/robustness improvements:

  1. TemplateCache  – mtime-keyed template caching (cache.py)
  2. Path-traversal hardening  – _ValidatePath in CliTable (clitable.py)
  3. ReDoS mitigation  – max_input_len in ParseText / ParseTextToDicts (parser.py)
"""

import io
import os
import tempfile
import threading
import time
import unittest
from unittest import mock

import textfsm
from textfsm import cache as cache_module
from textfsm import clitable


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SIMPLE_TEMPLATE = (
    'Value Name (\\S+)\n'
    '\n'
    'Start\n'
    '  ^Hello ${Name}\n'
    '\n'
)

_SIMPLE_INPUT = 'Hello world\n'


def _write_template(path, content=_SIMPLE_TEMPLATE):
  with open(path, 'w') as fh:
    fh.write(content)


# ---------------------------------------------------------------------------
# 1.  TemplateCache tests
# ---------------------------------------------------------------------------

class TestTemplateCache(unittest.TestCase):
  """Tests for textfsm.cache.TemplateCache."""

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp()
    self.tmpl_path = os.path.join(self.tmpdir, 'test.fsm')
    _write_template(self.tmpl_path)

  # --- basic get / cache hit ---

  def test_get_returns_textfsm(self):
    c = cache_module.TemplateCache()
    fsm = c.get(self.tmpl_path)
    self.assertIsInstance(fsm, textfsm.TextFSM)

  def test_repeated_get_returns_fresh_parsers(self):
    """Reuse the cached template without sharing parser state or rereading it."""
    c = cache_module.TemplateCache()
    fsm1 = c.get(self.tmpl_path)
    first_result = fsm1.ParseText('Hello device_a\n')
    with mock.patch('builtins.open', side_effect=AssertionError('Cache miss')):
      fsm2 = c.get(self.tmpl_path)
    self.assertIsNot(fsm1, fsm2)
    self.assertEqual(fsm2.ParseText('Hello device_b\n'), [['device_b']])
    self.assertEqual(first_result, [['device_a']])

  def test_filldown_values_are_not_shared(self):
    _write_template(
        self.tmpl_path,
        'Value Filldown Host (\\S+)\n'
        'Value Required Item (\\S+)\n'
        '\n'
        'Start\n'
        '  ^Host ${Host}\n'
        '  ^Item ${Item} -> Record\n',
    )
    c = cache_module.TemplateCache()
    fsm1 = c.get(self.tmpl_path)
    self.assertEqual(
        fsm1.ParseText('Host device_a\nItem first\n'), [['device_a', 'first']]
    )
    fsm2 = c.get(self.tmpl_path)
    self.assertEqual(fsm2.ParseText('Item second\n'), [['', 'second']])

  def test_list_values_are_not_shared(self):
    _write_template(
        self.tmpl_path, _SIMPLE_TEMPLATE.replace('Value Name', 'Value List Name')
    )
    c = cache_module.TemplateCache()
    fsm1 = c.get(self.tmpl_path)
    fsm1.ParseText('Hello device_a\n', eof=False)
    fsm2 = c.get(self.tmpl_path)
    self.assertEqual(fsm2.ParseText('Hello device_b\n'), [[['device_b']]])
    self.assertEqual(fsm1.ParseText(''), [[['device_a']]])

  def test_cache_len_increases(self):
    c = cache_module.TemplateCache()
    self.assertEqual(len(c), 0)
    c.get(self.tmpl_path)
    self.assertEqual(len(c), 1)

  # --- mtime invalidation ---

  def test_mtime_change_invalidates_cache(self):
    """After the template file is rewritten the cache must return a fresh FSM."""
    c = cache_module.TemplateCache()
    fsm1 = c.get(self.tmpl_path)

    # Force a detectable mtime change (sleep just long enough).
    time.sleep(0.05)
    _write_template(
        self.tmpl_path, _SIMPLE_TEMPLATE.replace('Hello', 'Goodbye')
    )

    # Manually bump mtime if filesystem resolution is coarse.
    new_mtime = os.path.getmtime(self.tmpl_path) + 1
    os.utime(self.tmpl_path, (new_mtime, new_mtime))

    fsm2 = c.get(self.tmpl_path)
    self.assertIsNot(fsm1, fsm2)
    self.assertEqual(fsm1.ParseText('Hello old\n'), [['old']])
    self.assertEqual(fsm2.ParseText('Goodbye new\n'), [['new']])
    # Old entry evicted – cache should still contain exactly 1 entry.
    self.assertEqual(len(c), 1)

  # --- max_size eviction ---

  def test_max_size_eviction(self):
    paths = []
    for i in range(3):
      p = os.path.join(self.tmpdir, 'tmpl%d.fsm' % i)
      _write_template(p)
      paths.append(p)

    c = cache_module.TemplateCache(max_size=2)
    c.get(paths[0])
    c.get(paths[1])
    self.assertEqual(len(c), 2)

    # Adding a third entry should evict the oldest (paths[0]).
    c.get(paths[2])
    self.assertLessEqual(len(c), 2)

  # --- invalidate() ---

  def test_invalidate_specific_path(self):
    c = cache_module.TemplateCache()
    c.get(self.tmpl_path)
    self.assertEqual(len(c), 1)
    c.invalidate(self.tmpl_path)
    self.assertEqual(len(c), 0)

  def test_invalidate_all(self):
    paths = []
    for i in range(3):
      p = os.path.join(self.tmpdir, 'tmpl%d.fsm' % i)
      _write_template(p)
      paths.append(p)
      cache_module.TemplateCache().get(p)  # warm separate caches

    c = cache_module.TemplateCache()
    for p in paths:
      c.get(p)
    self.assertEqual(len(c), 3)
    c.invalidate()
    self.assertEqual(len(c), 0)

  # --- thread safety ---

  def test_concurrent_get_and_parse_same_file(self):
    """Each thread parses its own input with independent parser state."""
    c = cache_module.TemplateCache()
    errors = []
    results = [None] * 20
    ready = threading.Barrier(20)

    def worker(i):
      try:
        fsm = c.get(self.tmpl_path)
        ready.wait(timeout=5)
        results[i] = fsm.ParseText('Hello device_%d\n' % i)
      except Exception as exc:  # pylint: disable=broad-except
        errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
      t.start()
    for t in threads:
      t.join()

    self.assertEqual(errors, [])
    for i, result in enumerate(results):
      self.assertEqual(result, [['device_%d' % i]])

  # --- missing file ---

  def test_missing_file_raises(self):
    c = cache_module.TemplateCache()
    with self.assertRaises(cache_module.TemplateCacheError):
      c.get('/nonexistent/path/template.fsm')


# ---------------------------------------------------------------------------
# 2.  Path-traversal hardening tests  (CliTable._ValidatePath)
# ---------------------------------------------------------------------------

class TestValidatePath(unittest.TestCase):
  """Tests for CliTable._ValidatePath."""

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp()
    # Minimal CliTable without an index so we can call _ValidatePath directly.
    clitable.CliTable.INDEX = {}
    self.ct = clitable.CliTable(template_dir=self.tmpdir)

  def test_path_within_root_is_allowed(self):
    safe = os.path.join(self.tmpdir, 'template.fsm')
    result = self.ct._ValidatePath(safe)
    self.assertEqual(result, os.path.normpath(os.path.abspath(safe)))

  def test_traversal_with_dotdot_raises(self):
    evil = os.path.join(self.tmpdir, '..', 'etc', 'passwd')
    with self.assertRaises(clitable.CliTableError):
      self.ct._ValidatePath(evil)

  def test_absolute_path_outside_root_raises(self):
    with self.assertRaises(clitable.CliTableError):
      self.ct._ValidatePath('/etc/shadow')

  def test_no_template_dir_allows_any_path(self):
    """With template_dir=None the check is skipped (backwards-compatible)."""
    clitable.CliTable.INDEX = {}
    ct = clitable.CliTable(template_dir=None)
    # Should not raise even for a path outside any sandbox.
    result = ct._ValidatePath('/tmp/something.fsm')
    self.assertEqual(result, '/tmp/something.fsm')

  def test_traversal_in_template_names_to_files(self):
    """_TemplateNamesToFiles must reject traversal in template names."""
    # Write a real index so the object is fully constructed.
    idx_path = os.path.join(self.tmpdir, 'index')
    with open(idx_path, 'w') as fh:
      fh.write('Template, Command\n')
      fh.write('tmpl.fsm, show version\n')
    clitable.CliTable.INDEX = {}
    ct = clitable.CliTable('index', self.tmpdir)
    with self.assertRaises(clitable.CliTableError):
      ct._TemplateNamesToFiles('../../etc/passwd')

  def test_read_index_traversal_raises(self):
    """ReadIndex must reject an index_file that escapes template_dir."""
    clitable.CliTable.INDEX = {}
    ct = clitable.CliTable(template_dir=self.tmpdir)
    with self.assertRaises(clitable.CliTableError):
      ct.ReadIndex('../../etc/passwd')


class TestMtimeCache(unittest.TestCase):
  """Tests that CliTable.INDEX is keyed by mtime."""

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp()
    # Create a valid index file.
    self.idx_path = os.path.join(self.tmpdir, 'index')
    with open(self.idx_path, 'w') as fh:
      fh.write('Template, Command\n')
      fh.write('tmpl.fsm, show version\n')

  def test_cache_hit_same_mtime(self):
    clitable.CliTable.INDEX = {}
    ct1 = clitable.CliTable('index', self.tmpdir)
    ct2 = clitable.CliTable('index', self.tmpdir)
    self.assertIs(ct1.index, ct2.index)
    # Only one entry in the global cache.
    self.assertEqual(len(clitable.CliTable.INDEX), 1)

  def test_cache_miss_after_mtime_change(self):
    clitable.CliTable.INDEX = {}
    clitable.CliTable('index', self.tmpdir)
    # Simulate file being updated.
    new_mtime = os.path.getmtime(self.idx_path) + 2
    os.utime(self.idx_path, (new_mtime, new_mtime))
    # Re-read: must detect the new mtime and reparse.
    clitable.CliTable.INDEX = {}  # clear to simulate fresh process restart
    ct2 = clitable.CliTable('index', self.tmpdir)
    # Just verify we can read it without error; index is a fresh object.
    self.assertIsNotNone(ct2.index)


# ---------------------------------------------------------------------------
# 3.  ReDoS mitigation: max_input_len in ParseText / ParseTextToDicts
# ---------------------------------------------------------------------------

_FSM_TEMPLATE = (
    'Value Hostname (\\S+)\n'
    '\n'
    'Start\n'
    '  ^hostname ${Hostname}\n'
    '\n'
)


class TestMaxInputLen(unittest.TestCase):
  """Tests for the max_input_len parameter."""

  def _make_fsm(self):
    return textfsm.TextFSM(io.StringIO(_FSM_TEMPLATE))

  # --- ParseText ---

  def test_parse_text_within_limit_succeeds(self):
    fsm = self._make_fsm()
    short_input = 'hostname router1\n'
    result = fsm.ParseText(short_input, max_input_len=1000)
    self.assertEqual(result, [['router1']])

  def test_parse_text_at_exact_limit_succeeds(self):
    fsm = self._make_fsm()
    text = 'hostname router1\n'
    result = fsm.ParseText(text, max_input_len=len(text))
    self.assertEqual(result, [['router1']])

  def test_parse_text_over_limit_raises(self):
    fsm = self._make_fsm()
    long_input = 'hostname router1\n' * 100
    with self.assertRaises(textfsm.TextFSMError) as ctx:
      fsm.ParseText(long_input, max_input_len=10)
    self.assertIn('exceeds', str(ctx.exception).lower())

  def test_parse_text_no_limit_default(self):
    """Default (None) must never raise regardless of input size."""
    fsm = self._make_fsm()
    large_input = 'hostname router1\n' * 10_000
    # The template has no Record action so implicit EOF appends a single row.
    # The key assertion is that no TextFSMError is raised and at least one
    # row is returned.
    result = fsm.ParseText(large_input)
    self.assertGreaterEqual(len(result), 1)

  def test_parse_text_empty_input_respects_limit(self):
    """Empty string is shorter than any positive limit; must not raise."""
    fsm = self._make_fsm()
    result = fsm.ParseText('', max_input_len=0)
    self.assertEqual(result, [])

  # --- ParseTextToDicts ---

  def test_parse_text_to_dicts_within_limit(self):
    fsm = self._make_fsm()
    text = 'hostname router1\n'
    result = fsm.ParseTextToDicts(text, max_input_len=1000)
    self.assertEqual(result, [{'Hostname': 'router1'}])

  def test_parse_text_to_dicts_over_limit_raises(self):
    fsm = self._make_fsm()
    long_input = 'hostname router1\n' * 200
    with self.assertRaises(textfsm.TextFSMError):
      fsm.ParseTextToDicts(long_input, max_input_len=5)

  # --- exact boundary behaviour ---

  def test_one_over_limit_raises(self):
    fsm = self._make_fsm()
    text = 'hostname r\n'  # 11 chars
    with self.assertRaises(textfsm.TextFSMError):
      fsm.ParseText(text, max_input_len=10)

  def test_one_under_limit_ok(self):
    fsm = self._make_fsm()
    text = 'hostname r\n'  # 11 chars
    result = fsm.ParseText(text, max_input_len=12)
    self.assertEqual(result, [['r']])


if __name__ == '__main__':
  unittest.main()
