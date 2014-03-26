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

# Our way of using namedtuple is confusing pylint.
# pylint: disable=no-member
# pylint: disable=protected-access

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
from pytypedecl.parse import node


# TODO: Implement a proper visitor interface, instead of having both
#              ExpandTemplates() and Process()


class TypeDeclUnit(node.Node('constants', 'classes', 'functions')):
  """Top level node. Holds a list of Function nodes.

  Attributes:
    constants: List of module-level constants.
    functions: List of functions defined in this type decl unit.
    classes: List of classes defined in this type decl unit.
  """

  def Lookup(self, name):
    """Convenience function: Look up a given name in the global namespace."""
    try:
      return self._name2item[name]
    except AttributeError:
      self._name2item = {}
      for x in self.constants + self.functions + self.classes:
        self._name2item[x.name] = x
      return self._name2item[name]

  def ExpandTemplates(self, rev_templates):
    return self._replace(
        classes=[c.ExpandTemplates(rev_templates) for c in self.classes],
        functions=[f.ExpandTemplates(rev_templates) for f in self.functions])


class Constant(node.Node('name', 'type')):
  __slots__ = ()

  def ExpandTemplates(self, rev_t):
    return self._replace(type=self.type.ExpandTemplates(rev_t))


class Class(node.Node('name', 'parents', 'methods', 'constants', 'template')):
  """A Python class. Corresponds to a class in a *.py file."""

  def Lookup(self, name):
    """Convenience function: Look up a given name in the global namespace."""
    try:
      return self._name2item[name]
    except AttributeError:
      self._name2item = {}
      for x in self.methods + self.constants:
        self._name2item[x.name] = x
      return self._name2item[name]

  def ExpandTemplates(self, rev_templates):
    return self._replace(type=self.type.ExpandTemplates(rev_t))


class Class(node.Node('name', 'parents', 'methods', 'constants', 'template')):

  def Lookup(self, name):
    """Convenience function: Look up a given name in the global namespace."""
    try:
      return self._name2item[name]
    except AttributeError:
      self._name2item = {}
      for x in self.methods + self.constants:
        self._name2item[x.name] = x
      return self._name2item[name]

  def ExpandTemplates(self, rev_templates):
    rev_t = [self.template] + rev_templates
    return self._replace(methods=[f.ExpandTemplates(rev_t)
                                  for f in self.methods],
                         constants=[c.ExpandTemplates(rev_t)
                                    for c in self.constants])


class Function(node.Node('name', 'signatures')):
  """A function or a method.

  Attributes:
    name: The name of this function.
    signatures: Possible list of parameter type combinations for this function.
  """
  __slots__ = ()

  def ExpandTemplates(self, rev_t):
    return self._replace(signatures=[f.ExpandTemplates(rev_t)
                                     for f in self.signatures])


class Signature(node.Node('params', 'return_type', 'exceptions', 'template',
                          'provenance')):
  """Represents an individual signature of a function.

  For overloaded functions, this is one specific combination of parameters.
  For non-overloaded functions, there is a 1:1 correspondence between function
  and signature.

  Attributes:
    name: The name of this function.
    params: The list of parameters for this function definition.
    return_type: The return type of this function.
    exceptions: List of exceptions for this function definition.
    template: names for bindings for bounded types in params/return_type
    provenance: TBD

  # TODO: define/implement provenance:
                     ... inferred
                     --- programmer-deleted
                     +++ locked (no need to look inside it ... all declarations
                         for this function must be marked with +++ or ---
                     (nothing) programmer-approved
  """
  __slots__ = ()

  def ExpandTemplates(self, rev_templates):
    rev_t = [self.template] + rev_templates
    return self._replace(
        params=[p.ExpandTemplates(rev_t) for p in self.params],
        return_type=self.return_type.ExpandTemplates(rev_t),
        exceptions=[e.ExpandTemplates(rev_t) for e in self.exceptions])


class ExceptionDef(node.Node('containing_type')):
  # TODO: remove this. We can just point to the type directly.
  """Represents an exception.

  Attributes:
    containing_type: The exception type.
  """
  __slots__ = ()

  def ExpandTemplates(self, rev_templates):
    return self._replace(
        containing_type=self.containing_type.ExpandTemplates(rev_templates))


class Parameter(node.Node('name', 'type')):
  """Represents a parameter of a function definition.

  Attributes:
    name: The name of the parameter.
    type: The type of the parameter.
  """
  __slots__ = ()

  def ExpandTemplates(self, rev_templates):
    return self._replace(type=self.type.ExpandTemplates(rev_templates))


class TemplateItem(node.Node('name', 'within_type', 'level')):
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


class BasicType(node.Node('containing_type')):
  """A wrapper for a type. """
  # TODO: Rename to "NamedType"
  __slots__ = ()

  def ExpandTemplates(self, rev_templates):
    for level, templ in enumerate(rev_templates):
      for t in templ:
        if self.containing_type == t.name:
          return t._replace(level=level)  # TemplateItem
    else:  # pylint: disable=useless-else-on-loop
      return self

  def __str__(self):
    return str(self.containing_type)

  def Process(self, processor):
    return processor.ProcessBasicType(self)


class Scalar(node.Node('value')):
  __slots__ = ()
  def ExpandTemplates(self, unused_rev_templates):
    return self


class UnionType(node.Node('type_list')):
  __slots__ = ()

  def ExpandTemplates(self, rev_templates):
    return self._replace(
        type_list=[t.ExpandTemplates(rev_templates) for t in self.type_list])

  def Process(self, processor):
    return processor.ProcessUnionType(self)


class IntersectionType(node.Node('type_list')):
  __slots__ = ()

  def ExpandTemplates(self, rev_templates):
    return self._replace(
        type_list=[t.ExpandTemplates(rev_templates) for t in self.type_list])

  def Process(self, processor):
    return processor.ProcessIntersectionType(self)


class GenericType1(node.Node('base_type', 'type1')):
  # TODO: rewrite this to allow arbitrary length arguments
  __slots__ = ()

  def ExpandTemplates(self, rev_templates):
    return self._replace(
        base_type=self.base_type.ExpandTemplates(rev_templates),
        type1=self.type1.ExpandTemplates(rev_templates))

  def Process(self, processor):
    return processor.ProcessGenericType1(self)


class GenericType2(node.Node('base_type', 'type1', 'type2')):
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


