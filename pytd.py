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


from pytypedecl.parse import node
from pytypedecl.parse import visitors


# TODO: Make ExpandTemplates() and Process() use visitors.


class TypeDeclUnit(node.Node('constants', 'classes', 'functions')):
  """Top level node. Holds a list of Function nodes.

  Attributes:
    constants: List of module-level constants.
    functions: List of functions defined in this type decl unit.
    classes: List of classes defined in this type decl unit.
  """

  def Lookup(self, name):
    """Convenience function: Look up a given name in the global namespace.

    Tries to find a constant, function or class by this name.

    Args:
      name: Name to look up.

    Returns:
      A Constant, Function or Class.

    Raises:
      KeyError: if this identifier doesn't exist.
    """
    # TODO: Remove. Change constants, classes and functions to dict.
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
  """Represents a class declaration."""

  def Lookup(self, name):
    """Convenience function: Look up a given name in the class namespace.

    Tries to find a method or constant by this name in the class.

    Args:
      name: Name to look up.

    Returns:
      A Constant or Function instance.

    Raises:
      KeyError: if this identifier doesn't exist in this class.
    """
    # TODO: Remove this. Make methods and constants dictionaries.
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
                          'has_optional', 'provenance')):
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
  """Represents "template name extends bounded_type".

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
  """A wrapper for a type."""
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


class HomogeneousContainerType(node.Node('base_type', 'element_type')):
  __slots__ = ()

  def ExpandTemplates(self, rev_templates):
    return self._replace(
        base_type=self.base_type.ExpandTemplates(rev_templates),
        element_type=self.element_type.ExpandTemplates(rev_templates))

  def Process(self, processor):
    return processor.ProcessHomogeneousContainerType(self)


class GenericType(node.Node('base_type', 'parameters')):
  __slots__ = ()

  def ExpandTemplates(self, rev_templates):
    return self._replace(
        base_type=self.base_type.ExpandTemplates(rev_templates),
        parameters=[p.ExpandTemplates(rev_templates) for p in self.parameters])

  def Process(self, processor):
    return processor.ProcessGenericType(self)


def Print(n):
  """Convert a PYTD node to a string."""
  v = visitors.PrintVisitor()
  return n.Visit(v)

