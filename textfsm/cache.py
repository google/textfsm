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

"""Template cache for TextFSM.

Provides a thread-safe cache that stores template text keyed by
(absolute_path, mtime).  When the template file is modified on disk the cached
entry is automatically invalidated and rebuilt on the next request, so callers
never need to manage cache lifetime manually.

Typical usage::

    cache = TemplateCache()

    # First call: reads and caches the template, then creates a fresh parser.
    fsm = cache.get('/path/to/template.fsm')

    # Subsequent calls: creates a fresh parser from the cached template text.
    fsm = cache.get('/path/to/template.fsm')

The cache is safe to share across threads.  Each returned parser has independent
state.  A single global instance ``_DEFAULT_CACHE`` is provided for convenience.
"""

import io
import os
import threading
import textfsm


class TemplateCacheError(Exception):
  """Raised when a template cannot be loaded or compiled."""


class TemplateCache:
  """Thread-safe cache of template text used to create fresh TextFSM instances.

  Entries are keyed by ``(absolute_path, mtime)`` where *mtime* is the
  integer modification-time reported by ``os.path.getmtime``.  Changing a
  template file on disk therefore automatically invalidates the stale entry
  without requiring any explicit cache-busting calls.

  Attributes:
    max_size: int, maximum number of entries to keep.  When the limit is
      reached the oldest entry (by insertion order) is evicted.  ``None``
      means unlimited.
  """

  def __init__(self, max_size=None):
    """Initialise a new TemplateCache.

    Args:
      max_size: int or None, maximum number of cached templates.
    """
    self.max_size = max_size
    # Maps (abs_path, mtime_int) -> template text (str).
    self._cache = {}
    # Tracks insertion order for LRU-style eviction.
    self._order = []
    self._lock = threading.Lock()

  # ------------------------------------------------------------------
  # Public API
  # ------------------------------------------------------------------

  def get(self, path):
    """Return a fresh TextFSM for *path*, using cached template text if present.

    Each call creates an independent parser, so results, current state and
    option values such as Filldown are never shared between callers.

    Args:
      path: str, filesystem path to a TextFSM template file.

    Returns:
      textfsm.TextFSM instance.

    Raises:
      TemplateCacheError: If *path* cannot be opened or compiled.
    """
    abs_path = os.path.abspath(path)
    try:
      mtime = int(os.path.getmtime(abs_path))
    except OSError as exc:
      raise TemplateCacheError(
          'Cannot stat template file %r: %s' % (abs_path, exc)
      ) from exc

    cache_key = (abs_path, mtime)

    with self._lock:
      if cache_key in self._cache:
        return self._compile(abs_path, self._cache[cache_key])

      # Read and validate the template before adding its text to the cache.
      try:
        with open(abs_path, 'r') as fh:
          template = fh.read()
      except OSError as exc:
        raise TemplateCacheError(
            'Failed to read template %r: %s' % (abs_path, exc)
        ) from exc
      fsm = self._compile(abs_path, template)

      # Always evict stale entries for the same path (different mtime).
      stale = [k for k in self._order if k[0] == abs_path]
      for k in stale:
        self._cache.pop(k, None)
        self._order.remove(k)

      # Evict oldest entry when the cache is full (max_size mode).
      if self.max_size is not None:
        while len(self._cache) >= self.max_size and self._order:
          evict_key = self._order.pop(0)
          self._cache.pop(evict_key, None)

      self._cache[cache_key] = template
      self._order.append(cache_key)
      return fsm

  def invalidate(self, path=None):
    """Remove cached entries.

    Args:
      path: str or None.  When given, only entries for that path are removed;
        otherwise the entire cache is cleared.
    """
    with self._lock:
      if path is None:
        self._cache.clear()
        self._order.clear()
      else:
        abs_path = os.path.abspath(path)
        stale = [k for k in list(self._cache) if k[0] == abs_path]
        for k in stale:
          del self._cache[k]
          self._order.remove(k)

  def __len__(self):
    with self._lock:
      return len(self._cache)

  # ------------------------------------------------------------------
  # Internal helpers
  # ------------------------------------------------------------------

  @staticmethod
  def _compile(abs_path, template):
    """Create a fresh TextFSM from template text loaded from *abs_path*.

    Raises:
      TemplateCacheError: On any template parse error.
    """
    try:
      return textfsm.TextFSM(io.StringIO(template))
    except textfsm.TextFSMTemplateError as exc:
      raise TemplateCacheError(
          'Failed to compile template %r: %s' % (abs_path, exc)
      ) from exc


# ---------------------------------------------------------------------------
# Module-level default instance.
# ---------------------------------------------------------------------------
_DEFAULT_CACHE = TemplateCache()
