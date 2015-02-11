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

"""Visitor(s) for walking ASTs."""

# pylint: disable=g-importing-member

import collections
import re
from .. import pytd


class PrintVisitor(object):
  """Visitor for converting ASTs back to pytd source code."""
  implements_all_node_types = True

  INDENT = " " * 4
  VALID_NAME = re.compile(r"^[a-zA-Z_]\w*$")

  def __init__(self):
    self.class_name = None

  def SafeName(self, name):
    if not self.VALID_NAME.match(name):
      # We can do this because name will never contain backticks. Everything
      # we process here came in through the pytd parser, and the pytd syntax
      # doesn't allow escaping backticks themselves.
      return "`%s`" % name
    else:
      return name

  @staticmethod
  def TemplateParameterString(parameters):
    # The syntax for a parameterized type with one parameter is "X<T,>"
    # (E.g. "tuple<int,>")
    return parameters[0] + ", " + ", ".join(parameters[1:])

  def VisitTypeDeclUnit(self, node):
    """Convert the AST for an entire module back to a string."""
    sections = [node.constants, node.functions,
                node.classes, node.modules.values()]
    sections_as_string = ("\n".join(section_suite)
                          for section_suite in sections
                          if section_suite)
    return "\n\n".join(sections_as_string)

  def VisitConstant(self, node):
    """Convert a class-level or module-level constant to a string."""
    return node.name + ": " + node.type

  def EnterClass(self, cls):
    self.class_name = self.SafeName(cls.name + self.ClassTemplateString(cls))

  def LeaveClass(self, _):
    self.class_name = None

  def ClassTemplateString(self, cls):
    return "<" + ", ".join(cls.template) + ">" if cls.template else ""

  def VisitClass(self, node):
    """Visit a class, producing a string.

    class name<template>(parents....):
      constants...
      methods...

    Args:
      node: class node
    Returns:
      string representation of this class
    """
    parents = "(" + ", ".join(node.parents) + ")" if node.parents else ""
    template = self.ClassTemplateString(node)
    if node.methods or node.constants:
      # We have multiple methods, and every method has multiple signatures
      # (i.e., the method string will have multiple lines). Combine this into
      # an array that contains all the lines, then indent the result.
      all_lines = sum((m.splitlines() for m in node.methods), [])
      constants = [self.INDENT + m for m in node.constants]
      methods = [self.INDENT + m for m in all_lines]
    else:
      constants = []
      methods = [self.INDENT + "pass"]
    header = "class " + self.SafeName(node.name) + template + parents + ":"
    return "\n".join([header] + constants + methods) + "\n"

  def VisitFunction(self, node):
    """Visit a function, producing a multi-line string (one for each signature).

    E.g.:
      def multiply(x:int, y:int) -> int
      def multiply(x:float, y:float) -> float

    Args:
      node: A function node.
    Returns:
      string representation of the function.
    """
    return "\n".join("def " + node.name + sig for sig in node.signatures)

  def VisitSignature(self, node):
    """Visit a signature, producing a string.

    E.g.:
      (x: int, y: int, z: unicode) -> str raises ValueError

    Args:
      node: signature node
    Returns:
      string representation of the signature (no "def" and function name)
    """
    # TODO: template

    # Potentially abbreviate. "?" is the default.
    ret = " -> " + node.return_type if node.return_type != "?" else ""

    exc = " raises " + ", ".join(node.exceptions) if node.exceptions else ""
    optional = ("...",) if node.has_optional else ()

    mutable_params = [p for p in self.old_node.params
                      if isinstance(p, pytd.MutableParameter)]
    if mutable_params:
      stmts = "\n".join(self.INDENT + name + " := " + new.Visit(PrintVisitor())
                        for name, _, new in mutable_params)
      body = ":\n" + stmts
    else:
      body = ""

    return "(" + ", ".join(node.params + optional) + ")" + ret + exc + body

  def VisitParameter(self, node):
    """Convert a function parameter to a string."""
    if node.type == "object":
      # Abbreviated form. "object" is the default.
      return node.name
    elif node.name == "self" and node.type == self.class_name:
      return node.name
    else:
      return node.name + ": " + node.type

  def VisitMutableParameter(self, node):
    """Convert a mutable function parameter to a string."""
    return self.VisitParameter(node)

  def VisitTemplateItem(self, node):
    """Convert a template (E.g. "<X extends list>") to a string."""
    if str(node.within_type) == "object":
      return node.type_param
    else:
      return node.type_param + " extends " + node.within_type

  def VisitNamedType(self, node):
    """Convert a type to a string."""
    return self.SafeName(node.name)

  def VisitNativeType(self, node):
    """Convert a native type to a string."""
    return self.SafeName(node.python_type.__name__)

  def VisitUnknownType(self, unused_node):
    """Convert an unknown type to a string."""
    return "?"

  def VisitNothingType(self, unused_node):
    """Convert the nothing type to a string."""
    return "nothing"

  def VisitClassType(self, node):
    return self.SafeName(node.name)

  def VisitTypeParameter(self, node):
    return self.SafeName(node.name)

  def VisitHomogeneousContainerType(self, node):
    """Convert a homogeneous container type to a string."""
    return node.base_type + "<" + node.element_type + ">"

  def VisitGenericType(self, node):
    """Convert a generic type (E.g. list<int>) to a string."""
    param_str = self.TemplateParameterString(node.parameters)
    return node.base_type + "<" + param_str + ">"

  def VisitUnionType(self, node):
    """Convert a union type ("x or y") to a string."""
    # TODO: insert parentheses if necessary (i.e., if the parent is
    # an intersection.)
    return " or ".join(node.type_list)

  def VisitIntersectionType(self, node):
    """Convert an intersection type ("x and y") to a string."""
    return " and ".join(node.type_list)


class StripSelf(object):
  """Transforms the tree into one where methods don't have the "self" parameter.

  This is useful for certain kinds of postprocessing and testing.
  """

  def VisitClass(self, node):
    """Visits a Class, and removes "self" from all its methods."""
    return node.Replace(methods=tuple(self._StripFunction(m)
                                      for m in node.methods))

  def _StripFunction(self, node):
    """Remove "self" from all signatures of a method."""
    return node.Replace(signatures=tuple(self.StripSignature(s)
                                         for s in node.signatures))

  def StripSignature(self, node):
    """Remove "self" from a Signature. Assumes "self" is the first argument."""
    return node.Replace(params=node.params[1:])


class _FillInClasses(object):
  """Fill in ClassType pointers using a symbol table.

  This is an in-place visitor! It modifies the original tree. This is
  necessary because we introduce loops.
  """

  def __init__(self, local_lookup, global_lookup):
    """Create this visitor.

    You're expected to then pass this instance to node.Visit().

    Args:
      local_lookup: Usually, the local module. Tried first when looking up
        names.
      global_lookup: Global symbols. Tried if a name doesn't exist locally.
    """
    self._local_lookup = local_lookup
    self._global_lookup = global_lookup

  def VisitClassType(self, node):
    """Fills in a class type.

    Args:
      node: A ClassType. This node will have a name, which we use for lookup.

    Returns:
      The same ClassType. We will have filled in its "cls" attribute.

    Raises:
      KeyError: If we can't find a given class.
    """
    if node.cls is None:
      try:
        node.cls = self._local_lookup.Lookup(node.name)
      except KeyError:
        try:
          node.cls = self._global_lookup.Lookup(node.name)
        except KeyError:
          pass
    return node


class NamedTypeToClassType(object):
  """Change all NamedType objects to ClassType objects."""

  def VisitNamedType(self, node):
    """Converts a named type to a class type, to be filled in later.

    Args:
      node: The NamedType. This type only has a name.

    Returns:
      A ClassType. This ClassType will (temporarily) only have a name.
    """
    return pytd.ClassType(node.name)


def FillInClasses(target, global_module=None):
  """Fill in class pointers in ClassType nodes for a PyTD object.

  Args:
    target: The PyTD object to operate on. Changes will happen in-place. If this
    is a TypeDeclUnit it will also be used for lookups.
    global_module: Global symbols. Tried if a name doesn't exist locally. This
    is required if target is not a TypeDeclUnit.
  """
  if global_module is None:
    global_module = target

  if hasattr(target, "modules"):
    for submodule in target.modules.values():
      FillInClasses(submodule, global_module)

  # Fill in classes for this module, bottom up.
  # TODO: Node.Visit() should support blacklisting of attributes so
  # we don't recurse into submodules multiple times.
  if isinstance(target, pytd.TypeDeclUnit):
    target.Visit(_FillInClasses(target, global_module))
  else:
    target.Visit(_FillInClasses(global_module, global_module))


def LookupClasses(module):
  """Converts a module from one using NamedType to ClassType.

  Args:
    module: The module to process.

  Returns:
    A new module that only uses ClassType. All ClassType instances will point
    to concrete classes.

  Throws:
    KeyError: If we can't find a class.
  """
  module = module.Visit(NamedTypeToClassType())
  FillInClasses(module, module)
  return module


class ReplaceTypes(object):
  """Visitor for replacing types in a tree.

  This replaces both NamedType and ClassType nodes that have a name in the
  mapping. The two cases are not distinguished.
  """

  def __init__(self, mapping):
    self.mapping = mapping

  def VisitNamedType(self, node):
    return self.mapping.get(node.name, node)

  def VisitClassType(self, node):
    return self.mapping.get(node.name, node)

  # We do *not* want to have 'def VisitClass' because that will replace a class
  # definition with itself, which is almost certainly not what is wanted,
  # because runing pytd.Print on it will result in output that's just a list of
  # class names with no contents.


class RemoveTemplates(object):
  """Visitor for removing all templates from an AST.

  This is a destructive operation.
  """

  def VisitHomogeneousContainerType(self, node):
    return node.base_type

  def VisitGenericType(self, node):
    return node.base_type


class ExtractSuperClasses(object):
  """Visitor for extracting all superclasses (i.e., the class hierarchy)."""

  def VisitTypeDeclUnit(self, module):
    result = {base_class: superclasses
              for base_class, superclasses in module.classes}
    for module_name, module_dict in module.modules:
      result.update({module_name + "." + name: superclasses
                     for name, superclasses in module_dict.items()})
    return result

  def VisitClass(self, cls):
    return (cls.name, [parent.name for parent in cls.parents])


class ReplaceTypeParameters(object):
  """Visitor for replacing type parameters with actual types."""

  def __init__(self, mapping):
    self.mapping = mapping

  def VisitTypeParameter(self, p):
    return self.mapping[p]


class InstantiateTemplatesVisitor(object):
  """Tries to remove templates by instantiating the corresponding types.

  It will create classes that are named "base_type<element_type>", so e.g.
  a list of integers will literally be named "list<int>".

  Attributes:
    symbol_table: Symbol table for looking up templated classes.
  """

  def __init__(self):
    self.classes_to_instantiate = collections.OrderedDict()

  def _InstantiatedClass(self, name, node, symbol_table):
    cls = symbol_table.Lookup(node.base_type.name)
    mapping = {t.type_param: e for t, e in zip(cls.template, node.parameters)}
    return cls.Replace(name=name, template=()).Visit(
        ReplaceTypeParameters(mapping))

  def InstantiatedClasses(self, symbol_table):
    return [self._InstantiatedClass(name, node, symbol_table)
            for name, node in self.classes_to_instantiate.items()]

  def VisitHomogeneousContainerType(self, node):
    """Converts a template type (container type) to a concrete class.

    This works by looking up the actual Class (using the lookup table passed
    when initializing the visitor) and substituting the parameters of the
    template everywhere in its definition. The new class is appended to the
    list of classes of this module. (Later on, the template we used is removed.)

    Args:
      node: An instance of HomogeneousContainerType

    Returns:
      A new NamedType pointing to an instantiation of the class.
    """
    name = node.Visit(PrintVisitor())
    if name not in self.classes_to_instantiate:
      self.classes_to_instantiate[name] = node
    return pytd.NamedType(name)

  def VisitGenericType(self, node):
    """Converts a parameter-based template type (e.g. dict<str,int>) to a class.

    This works by looking up the actual Class (using the lookup table passed
    when initializing the visitor) and substituting the parameters of the
    template everywhere in its definition. The new class is appended to the
    list of classes of this module. (Later on, also all templates are removed.)

    Args:
      node: An instance of GenericType.

    Returns:
      A new NamedType pointing to an instantiation of the class.
    """
    name = node.Visit(PrintVisitor())
    if name not in self.classes_to_instantiate:
      self.classes_to_instantiate[name] = node
    return pytd.NamedType(name)


def InstantiateTemplates(node):
  """Adds the instantiated classes to the module. Removes templates.

  This will add the instantiated classes to the module the original was
  defined in.

  Args:
    node: Module to process. The elements of this module will already be
      processed once this method is called.

  Returns:
    A module that contains extra classes for all the templated classes
    we encountered within this module.
  """
  v = InstantiateTemplatesVisitor()
  node = node.Visit(v)
  old_classes = [c for c in node.classes if not c.template]
  new_classes = v.InstantiatedClasses(node)
  return node.Replace(classes=old_classes + new_classes)


def ClassAsType(cls):
  """Converts a pytd.Class to an instance of pytd.Type."""
  if not cls.template:
    return pytd.NamedType(cls.name)
  elif len(cls.template) == 1:
    params = tuple(pytd.NamedType(item.name) for item in cls.template)
    return pytd.HomogeneousContainerType(pytd.NamedType(cls.name),
                                         params)
  else:  # len(cls.template) >= 2
    params = tuple(pytd.NamedType(item.name) for item in cls.template)
    return pytd.GenericType(pytd.NamedType(cls.name), params)


class AdjustSelf(object):
  """Visitor for setting the correct type on self.

  So
    class A:
      def f(self: object)
  becomes
    class A:
      def f(self: A)
  .
  (Notice the latter won't be printed like this, as printing simplifies the
   first argument to just "self")
  """

  def __init__(self, replace_unknown=False, force=False):
    self.class_type = None
    self.force = force
    self.replaced_self_types = (pytd.NamedType("object"),
                                pytd.ClassType("object"))
    if replace_unknown:
      self.replaced_self_types += (pytd.UnknownType(),)

  def EnterClass(self, cls):
    self.class_type = ClassAsType(cls)

  def LeaveClass(self, _):
    self.class_type = None

  def VisitMutableParameter(self, p):
    p2 = self.VisitParameter(p)
    return pytd.MutableParameter(p2.name, p2.type, p.new_type)

  def VisitParameter(self, p):
    """Adjust all parameters called "self" to have their parent class type.

    But do this only if their original type is unoccupied ("object" or,
    if configured, "?").

    Args:
      p: pytd.Parameter instance.

    Returns:
      Adjusted pytd.Parameter instance.
    """
    if not self.class_type:
      # We're not within a class, so this is not a parameter of a method.
      return p
    if p.name == "self" and (self.force or p.type in self.replaced_self_types):
      return pytd.Parameter("self", self.class_type)
    else:
      return p


class RemoveUnknownClasses(object):
  """Visitor for converting ClassTypes called ~unknown* to just UnknownType.

  For example, this will change
    def f() -> ~unknown1
    class ~unknown1:
      ...
  to
    def f() -> ?
  """

  def VisitClassType(self, t):
    if t.name.startswith("~unknown"):
      return pytd.UnknownType()
    else:
      return t

  def VisitNamedType(self, t):
    if t.name.startswith("~unknown"):
      return pytd.UnknownType()
    else:
      return t

  def VisitClass(self, cls):
    if cls.name.startswith("~unknown"):
      return None
    return cls

  def VisitTypeDeclUnit(self, u):
    return u.Replace(classes=tuple(cls for cls in u.classes if cls is not None))
