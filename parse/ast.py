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


class TypeDeclUnit(typed_tuple.Eq, collections.namedtuple(
    'TypeDeclUnit', ['interfacedefs', 'classdefs', 'funcdefs'])):
  """Top level node. Holds a list of Function nodes.

  Attributes:
    funcdefs: A list of functions defined in this type decl unit.
    interfacedefs: A list of interfaces defined in this type decl unit.
    classdefs: A list of interfaces defined in this type decl unit.
  """
  __slots__ = ()

  def ExpandTemplates(self, rev_templates):
    return self._replace(
        interfacedefs=[i.ExpandTemplates(rev_templates)
                       for i in self.interfacedefs],
        classdefs=[c.ExpandTemplates(rev_templates) for c in self.classdefs],
        funcdefs=[f.ExpandTemplates(rev_templates) for f in self.funcdefs])


class Interface(typed_tuple.Eq, collections.namedtuple(
    'Interface', ['name', 'parents', 'attrs', 'template'])):
  __slots__ = ()

  def ExpandTemplates(self, rev_templates):
    rev_t = [self.template] + rev_templates
    return self._replace(attrs=[a.ExpandTemplates(rev_t) for a in self.attrs])


class Class(typed_tuple.Eq, collections.namedtuple(
    'Class', ['name', 'parents', 'funcs', 'template'])):
  __slots__ = ()

  def ExpandTemplates(self, rev_templates):
    rev_t = [self.template] + rev_templates
    return self._replace(funcs=[f.ExpandTemplates(rev_t) for f in self.funcs])


class Function(typed_tuple.Eq, collections.namedtuple(
    'Function', ['name', 'params', 'return_type', 'exceptions', 'template',
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
  __slots__ = ()

  def ExpandTemplates(self, rev_templates):
    rev_t = [self.template] + rev_templates
    return self._replace(
        params=[p.ExpandTemplates(rev_t) for p in self.params],
        return_type=self.return_type.ExpandTemplates(rev_t),
        exceptions=[e.ExpandTemplates(rev_t) for e in self.exceptions])


class ConstantDef(typed_tuple.Eq, collections.namedtuple(
    'ConstantDef', ['name', 'type'])):
  __slots__ = ()


class MinimalFunction(typed_tuple.Eq, collections.namedtuple(
    'MinimalFunction', ['name'])):
  """Like Function, but without params etc."""
  __slots__ = ()

  def ExpandTemplates(self, unused_rev_templates):
    return self


class ExceptionDef(typed_tuple.Eq, collections.namedtuple(
    'ExceptionDef', ['containing_type'])):
  """Represents an exception.

  Attributes:
    name: The exception typ.
  """
  __slots__ = ()

  def ExpandTemplates(self, rev_templates):
    return self._replace(
        containing_type=self.containing_type.ExpandTemplates(rev_templates))


class Parameter(typed_tuple.Eq, collections.namedtuple(
    'Parameter', ['name', 'type'])):
  """Represents a parameter of a function definition.

  Attributes:
    name: The name of the parameter.
    type: The type of the parameter.
  """
  __slots__ = ()

  def ExpandTemplates(self, rev_templates):
    return self._replace(type=self.type.ExpandTemplates(rev_templates))


class TemplateItem(typed_tuple.Eq, collections.namedtuple(
    'TemplateItem', ['name', 'within_type', 'level'])):
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
  __slots__ = ()

  def ExpandTemplates(self, rev_templates):
    return self._replace(self.within_type.ExpandTemplates(rev_templates))

  def Process(self, processor):
    return processor.ProcessTemplateItem(self)
