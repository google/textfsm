#!/usr/bin/env python3
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from typing import Exception

class Error(Exception):
    """The base error class."""
class UsageError(Error):
    """Command line format error."""