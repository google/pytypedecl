# -*- coding:utf-8; python-indent:2; indent-tabs-mode:nil -*-

# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Utilities for parsing type declaration files.
"""


from pytypedecl import utils
from pytypedecl.parse import parser


def GetBuiltins():
  """Get the "default" AST used to lookup built in types.

  Get an AST for all Python builtins as well as the most commonly used standard
  libraries.

  Returns:
    A pytd.TypeDeclUnit instance. It'll directly contain the builtin classes
    and functions, and submodules for each of the standard library modules.
  """
  builtins = parser.parse_file(utils.GetDataFile("builtins/__builtin__.pytd"))
  for mod in [
      "array", "errno", "fcntl", "gc", "itertools", "marshal", "posix", "pwd",
      "select", "signal", "_sre", "_struct", "strop", "sys", "_warnings",
      "_weakref"]:
    builtins.modules[mod] = parser.parse_file(
        utils.GetDataFile("builtins/" + mod + ".pytd"))
  return builtins
