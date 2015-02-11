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


# TODO: Rename this file to builtins.py.


"""Utilities for parsing type declaration files.
"""

import os.path

from pytypedecl import utils
from pytypedecl.parse import parser
from pytypedecl.parse import visitors


def _FindBuiltinFile(name):
  return utils.GetDataFile(os.path.join("builtins", name))


def GetBuiltins():
  """Get the "default" AST used to lookup built in types.

  Get an AST for all Python builtins as well as the most commonly used standard
  libraries.

  Returns:
    A pytd.TypeDeclUnit instance. It'll directly contain the builtin classes
    and functions, and submodules for each of the standard library modules.
  """
  # TODO: This can be fairly slow; suggest pickling the result and
  #                  reusing if possible (see lib2to3.pgen2.grammar)

  # We use the same parser instance to parse all builtin files. This changes
  # the run time from 1.0423s to 0.5938s (for 21 builtins).
  p = parser.TypeDeclParser(parser.DEFAULT_VERSION)
  builtins = p.Parse(_FindBuiltinFile("__builtin__.pytd"))
  # We list modules explicitly, because we might have to extract them out of
  # a PAR file, which doesn't have good support for listing directories.
  modules = ["array", "codecs", "errno", "fcntl", "gc", "itertools", "marshal",
             "os", "posix", "pwd", "select", "signal", "_sre", "StringIO",
             "strop", "_struct", "sys", "_warnings", "warnings", "_weakref"]
  for mod in modules:
    builtins.modules[mod] = p.Parse(_FindBuiltinFile(mod + ".pytd"))
  return builtins


def GetBuiltinsHierarchy():
  builtins = ParseBuiltinsFile("__builtin__.pytd")
  return builtins.Visit(visitors.ExtractSuperClasses())


def ParseBuiltinsFile(filename):
  """GetBuiltins(), but for a single file, not adding to builtins.modules."""
  return parser.parse_string(_FindBuiltinFile(filename))
