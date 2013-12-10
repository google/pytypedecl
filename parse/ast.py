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


class PyOptInterfaceDef(typed_tuple.Eq, collections.namedtuple(
    'PyOptInterfaceDef', ['name', 'parents', 'attrs'])):
  pass


class PyOptClassDef(typed_tuple.Eq, collections.namedtuple(
    'PyOptClassDef', ['name', 'parents', 'funcs'])):
  pass


class PyOptFuncDef(typed_tuple.Eq, collections.namedtuple(
    'PyOptFuncDef', ['name', 'params', 'return_type', 'exceptions', 'where',
                     'provenance', 'signature'])):
  """Represents a function definition.

  Attributes:
    name: The name of this function.
    params: The list of parameters for this function definition.
    return_type: The return type of this function.
    exceptions: A list of exceptions for this function definition.
    where: names for bindings for bounded types in params/return_type
    provenance: TBD
    signature: TBD

  # TODO: define/implement provenance:
                     ... inferred
                     --- programmer-deleted
                     +++ locked (no need to look inside it ... all declarations
                         for this function must be marked with +++ or ---
                     (nothing) programmer-approved
  # TODO: implement signature
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


class PyWhereItem(typed_tuple.Eq, collections.namedtuple(
    'PyWhereItem', ['name', 'within_type'])):
  """Represents "where name <= bounded_type".

  Attributes:
    name: the name that's used in a generic type
    type: the "<=" type for this name (e.g., BasicType('object'))
  """
