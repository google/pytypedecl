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


"""AST representation of a pytd file.

Each type has a Process method that takes a 'processor', which implements the
necessary callbacks. In this way, the processor can keep state, and can be used
to do node-specific processing, such as pretty-printing or creating constraints.
Typically, the caller will walk the tree and call itself via the Process
method. For example:

    class Printer(object):

      def WalkFunc(self, func):
        Print(func.name, ', '.join(p.type.Process(self) for p in func.params))

      # The Process callbacks:

      def ProcessBasicType(self, t):
        return t.containing_type

      def ProcessUnionType(self, t):
        return 'UNION({})'.format(', '.join(
            u.Process(self) for u in t.type_list))

      ... etc. ...

The ExpandTemplates method is used to look up names in the AST and replace them
by TemplateItem from the look-up. The 'rev_templates' argument is the list
of templates in reverse order (most recent one first).
"""


import collections
from pytypedecl.parse import typed_tuple


# TODO: Implement a proper visitor interface, instead of having both
#              ExpandTemplates() and Process()


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


class BasicType(typed_tuple.Eq, collections.namedtuple(
    'BasicType', ['containing_type'])):
  __slots__ = ()

  def ExpandTemplates(self, rev_templates):
    for level, templ in enumerate(rev_templates):
      for t in templ:
        if self.containing_type == t.name:
          return t._replace(level=level)  # TemplateItem
    else:
      return self

  def Process(self, processor):
    return processor.ProcessBasicType(self)


class ConstType(typed_tuple.Eq, collections.namedtuple(
    'ConstType', ['value'])):
  __slots__ = ()

  def ExpandTemplates(self, unused_rev_templates):
    return self

  def Process(self, processor):
    return processor.ProcessConstType(self)


class NoneAbleType(typed_tuple.Eq, collections.namedtuple(
    'NoneAbleType', ['base_type'])):
  __slots__ = ()

  def ExpandTemplates(self, unused_rev_templates):
    return self

  def Process(self, processor):
    return processor.ProcessNonableType(self)


class UnionType(typed_tuple.Eq, collections.namedtuple(
    'UnionType', ['type_list'])):
  __slots__ = ()

  def ExpandTemplates(self, rev_templates):
    return self._replace(
        type_list=[t.ExpandTemplates(rev_templates) for t in self.type_list])

  def Process(self, processor):
    return processor.ProcessUnionType(self)


class IntersectionType(typed_tuple.Eq, collections.namedtuple(
    'IntersectionType', ['type_list'])):
  __slots__ = ()

  def ExpandTemplates(self, rev_templates):
    return self._replace(
        type_list=[t.ExpandTemplates(rev_templates) for t in self.type_list])

  def Process(self, processor):
    return processor.ProcessIntersectionType(self)


class StructType(typed_tuple.Eq, collections.namedtuple(
    'StructType', ['ops'])):
  __slots__ = ()

  # There's no ExpandTemplates method because StructType isn't
  # created by the parser.

  def Process(self, processor):
    return processor.ProcessStructType(self)

  # Extra initialization ... see
  # http://stackoverflow.com/questions/3624753/how-to-provide-additional-initialization-for-a-subclass-of-namedtuple

  def __new__(cls, ops):
    return super(StructType, cls).__new__(cls, sorted(set(ops)))


class GenericType1(typed_tuple.Eq, collections.namedtuple(
    'GenericType1', ['base_type', 'type1'])):
  __slots__ = ()

  def ExpandTemplates(self, rev_templates):
    return self._replace(
        base_type=self.base_type.ExpandTemplates(rev_templates),
        type1=self.type1.ExpandTemplates(rev_templates))

  def Process(self, processor):
    return processor.ProcessGenericType1(self)


class GenericType2(typed_tuple.Eq, collections.namedtuple(
    'GenericType2', ['base_type', 'type1', 'type2'])):
  """Constructor for types taking two type arguments.

  Attributes:
    base_type: type that is parameterized. E.g. dict
    type1: first type parameter. E.g. dict[type1, type2]
    type2: second type parameter. E.g. dict[type1, type2]
  """
  __slots__ = ()

  def ExpandTemplates(self, rev_templates):
    return self._replace(
        base_type=self.base_type.ExpandTemplates(rev_templates),
        type1=self.type1.ExpandTemplates(rev_templates),
        type2=self.type2.ExpandTemplates(rev_templates))

  def Process(self, processor):
    return processor.ProcessGenericType2(self)


class UnknownType(typed_tuple.Eq, collections.namedtuple('UnknownType', '')):
  __slots__ = ()

  def ExpandTemplates(self, unused_rev_templatesn):
    return self

  def Process(self, processor):
    return processor.ProcessUnknownType(self)


class OptionalUnknownType(typed_tuple.Eq,
                          collections.namedtuple('OptionalUnknownType', '')):
  __slots__ = ()

  def ExpandTemplates(self, unused_rev_templatesn):
    return self

  def Process(self, processor):
    return processor.ProcessOptionalUnknownType(self)


class VarArgType(OptionalUnknownType):
  """*args"""
  __slots__ = ()


class VarKeywordArgType(OptionalUnknownType):
  """**kwargs"""
  __slots__ = ()
