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

import itertools
from pytypedecl.parse import parser


class ParserUtils(object):
  """A utility class for parsing type declaration files.
  """

  def __init__(self):
    self._parser = parser.PyParser()

  def LoadTypeDeclaration(self, content):
    """Parse a type declaration from a str.

    Args:
      content: type declaration to parse

    Returns:
      A tuple of interfaces dict[str, PyOptInterfaceDef],
                 classes    dict[str, PyOptClassDef],
                 functions  dict[str, PyOptFuncdef]
    """
    type_decl_unit = self._parser.Parse(content)
    functions_by_name = {f_name: list(g) for f_name, g
                         in itertools.groupby(
                             type_decl_unit.funcdefs.list_funcdef,
                             lambda f: f.name)}

    interface_by_name = {i.name: i for i
                         in type_decl_unit.interfacedefs.list_interfacedef}

    class_by_name = {c.name: c for c
                     in type_decl_unit.classdefs.list_classdef}
    # TODO(rgurma): make this a named_tuple
    return (interface_by_name, class_by_name, functions_by_name)

  def LoadTypeDeclarationFromFile(self, type_decl_path):
    """Parse a type declaration and convert it to a list of functions.

    Args:
      type_decl_path: type declaration to parse

    Returns:
      A tuple of interfaces dict[str, PyOptInterfaceDef],
                 classes    dict[str, PyOptClassDef],
                 functions  dict[str, PyOptFuncdef]
    """
    with open(type_decl_path) as f:
      return self.LoadTypeDeclaration(f.read())
