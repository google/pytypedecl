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

import collections
import itertools
import sys
import traceback
from pytypedecl.parse import parser


InterfacesClassesFuncsByName = collections.namedtuple(
    'InterfacesClassesFuncsByName',
    ['interfaces', 'classes', 'funcs'])


class ParserUtils(object):
  """A utility class for parsing type declaration files.

  If there's an error, prints a message and calls sys.exit(1)
  """

  def __init__(self):
    self._parser = parser.PyParser()

  def LoadTypeDeclaration(self, content, filename=''):
    """Parse a type declaration from a str.

    Args:
      content:  string: type declarations to parse
      filename: name of the file whose content is in 'content'

    Returns:
      A tuple of interfaces dict[str, Interface],
                 classes    dict[str, Class],
                 functions  dict[str, PyOptFuncdef]
    """
    # TODO: There is an inconsistency here ... the functions are
    #                  grouped by named but this isn't done for the functions
    #                  (methods) inside a class or interface.  Add grouping to
    #                  class/interface and change the pytd-to-constraints
    #                  compiler to use this for detecting polymorphic functions
    #                  and methods.
    try:
      type_decl_unit = self._parser.Parse(content, filename)
    except SyntaxError as unused_exception:
      # without all the tedious traceback stuff from PLY:
      traceback.print_exception(sys.exc_type, sys.exc_value, None)
      sys.exit(1)

    functions_by_name = {f_name: list(g) for f_name, g
                         in itertools.groupby(
                             type_decl_unit.funcdefs,
                             lambda f: f.name)}

    interface_by_name = {i.name: i for i in type_decl_unit.interfacedefs}

    class_by_name = {c.name: c for c in type_decl_unit.classdefs}

    return InterfacesClassesFuncsByName(
        interfaces=interface_by_name,
        classes=class_by_name,
        funcs=functions_by_name)

  def LoadTypeDeclarationFromFile(self, type_decl_path):
    """Parse a type declaration and convert it to a list of functions.

    Args:
      type_decl_path: type declaration to parse

    Returns:
      A tuple of interfaces dict[str, Interface],
                 classes    dict[str, Class],
                 functions  dict[str, PyOptFuncdef]
    """
    with open(type_decl_path) as f:
      return self.LoadTypeDeclaration(f.read(), type_decl_path)
