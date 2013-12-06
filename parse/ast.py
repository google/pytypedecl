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


"""Classes used by parser to generate an AST.

The __repr__ definition aren't required by PLY.
They are useful for testing & debugging.
"""

import collections
from pytypedecl.parse import typed_tuple


class PyOptTypeDeclUnit(typed_tuple.Eq, collections.namedtuple(
    'PyOptTypeDeclUnit', ['interfacedefs', 'classdefs', 'funcdefs'])):
  """Top level node. Holds a list of FuncDef nodes.

  Attributes:
    funcdefs: A list of function defined in this type decl unit.
    interfacedefs: A list of interface defined in this type decl unit.
  """


class PyOptInterfaceDefs(typed_tuple.Eq, collections.namedtuple(
    'PyOptInterfaceDefs', ['list_interfacedef'])):

  def AddInterfaceDef(self, interfacedef):
    self.list_interfacedef.append(interfacedef)


class PyOptInterfaceDef(typed_tuple.Eq, collections.namedtuple(
    'PyOptInterfaceDef', ['name', 'parents', 'attrs'])):
  pass


class PyOptClassDefs(typed_tuple.Eq, collections.namedtuple(
    'PyOptClassDefs', ['list_classdef'])):

  def AddClassDef(self, classdef):
    self.list_classdef.append(classdef)


class PyOptClassDef(typed_tuple.Eq, collections.namedtuple(
    'PyOptClassDef', ['name', 'funcs'])):
  pass


class PyOptFuncDefs(typed_tuple.Eq, collections.namedtuple(
    'PyOptFuncDefs', ['list_funcdef'])):

  def AddFuncDef(self, funcdef):
    self.list_funcdef.append(funcdef)


class PyOptFuncDef(typed_tuple.Eq, collections.namedtuple(
    'PyOptFuncDef', ['name', 'params', 'return_type', 'exceptions'])):
  """Represents a function definition.

  Attributes:
    name: The name of this function.
    params: The list of parameters for this function definition.
    return_type: The return type of this function.
    exceptions: A list of exceptions for this function definition.
  """


class PyOptException(typed_tuple.Eq, collections.namedtuple(
    'PyOptException', ['name'])):
  """Represents an exception.

  Attributes:
    name: The name of this exception.
  """


class PyOptParam(typed_tuple.Eq, collections.namedtuple(
    'PyOptParam', ['name', 'type'])):
  """Represents a parameter of a function definition.

  Attributes:
    name: The name of the parameter.
    type: The type of the parameter.
  """


class PyOptIdentifier(typed_tuple.Eq, collections.namedtuple(
    'PyOptIdentifier', ['identifier_str'])):
  """Represents an identifier.

  Attributes:
    identifier_str: String of the identifier.
  """
