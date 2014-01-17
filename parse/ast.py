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

# TODO: Combine with the 'typing' module?


"""Classes used by parser to generate an AST.
"""

import collections
from pytypedecl.parse import typed_tuple


class PyOptTypeDeclUnit(typed_tuple.Eq, collections.namedtuple(
    'PyOptTypeDeclUnit', ['interfacedefs', 'classdefs', 'funcdefs'])):
  """Top level node. Holds a list of FuncDef nodes.

  Attributes:
    funcdefs: A list of functions defined in this type decl unit.
    interfacedefs: A list of interfaces defined in this type decl unit.
    classdefs: A list of interfaces defined in this type decl unit.
  """

  def ExpandTemplates(self, rev_templates):
    return self._replace(
        interfacedefs=[i.ExpandTemplates(rev_templates)
                       for i in self.interfacedefs],
        classdefs=[c.ExpandTemplates(rev_templates) for c in self.classdefs],
        funcdefs=[f.ExpandTemplates(rev_templates) for f in self.funcdefs])

class PyOptInterfaceDef(typed_tuple.Eq, collections.namedtuple(
    'PyOptInterfaceDef', ['name', 'parents', 'attrs', 'template'])):

  def ExpandTemplates(self, rev_templates):
    rev_t = [self.template] + rev_templates
    return self._replace(attrs=[a.ExpandTemplates(rev_t) for a in self.attrs])


class PyOptClassDef(typed_tuple.Eq, collections.namedtuple(
    'PyOptClassDef', ['name', 'parents', 'funcs', 'template'])):

  def ExpandTemplates(self, rev_templates):
    rev_t = [self.template] + rev_templates
    return self._replace(funcs=[f.ExpandTemplates(rev_t) for f in self.funcs])


class PyOptFuncDef(typed_tuple.Eq, collections.namedtuple(
    'PyOptFuncDef', ['name', 'params', 'return_type', 'exceptions', 'template',
                     'provenance', 'signature'])):
  """Represents a function definition.

  Attributes:
    name: The name of this function.
    params: The list of parameters for this function definition.
    return_type: The return type of this function.
    exceptions: A list of exceptions for this function definition.
    template: names for bindings for bounded types in params/return_type
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

  def ExpandTemplates(self, rev_templates):
    rev_t = [self.template] + rev_templates
    return self._replace(
        params=[p.ExpandTemplates(rev_t) for p in self.params],
        return_type=self.return_type.ExpandTemplates(rev_t),
        exceptions=[e.ExpandTemplates(rev_t) for e in self.exceptions])


class PyOptFuncDefMinimal(typed_tuple.Eq, collections.namedtuple(
    'PyOptFuncDefMinimal', ['name'])):
  """Like PyOptFuncDef, but without params etc."""

  def ExpandTemplates(self, rev_templates):
    return self


class PyOptException(typed_tuple.Eq, collections.namedtuple(
    'PyOptException', ['containing_type'])):
  """Represents an exception.

  Attributes:
    name: The exception typ.
  """

  def ExpandTemplates(self, rev_templates):
    return self._replace(
        containing_type=self.containing_type.ExpandTemplates(rev_templates))


class PyOptParam(typed_tuple.Eq, collections.namedtuple(
    'PyOptParam', ['name', 'type'])):
  """Represents a parameter of a function definition.

  Attributes:
    name: The name of the parameter.
    type: The type of the parameter.
  """

  def ExpandTemplates(self, rev_templates):
    return self._replace(type=self.type.ExpandTemplates(rev_templates))


class PyTemplateItem(typed_tuple.Eq, collections.namedtuple(
    'PyTemplateItem', ['name', 'within_type', 'level'])):
  """Represents "template name <= bounded_type".

  This can be either the result of the 'template' in the parser (e.g.,
    funcdef : provenance DEF template NAME LPAREN params RPAREN ...)
  or the result of a lookup using the ExpandTemplates method.

  Attributes:
    name: the name that's used in a generic type
    type: the "<=" type for this name (e.g., BasicType('object'))
    level: When this object is the result of a lookup, it is how many
           levels "up" the name was found. For example:
             class [T] Foo:
               def [U] bar(t: T, u: U)
           in the definition of 'bar', T has level=1 and U has level=0
  """

  def ExpandTemplates(self, rev_templates):
    return self._replace(self.within_type.ExpandTemplates(rev_templates))

  def Process(self, processor):
    return processor.ProcessTemplateItem(self)
