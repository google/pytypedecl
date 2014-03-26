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


class PrintVisitor(object):
  """Visitor for converting ASTs back to pytd source code."""

  INDENT = " "*4

  def VisitTypeDeclUnit(self, node):
    """Convert the AST for an entire pytd file back to a string."""
    return "\n".join(node.constants + node.classes + node.functions)

  def VisitConstant(self, node):
    """Convert a class-level or module-level constant to a string."""
    return node.name + ": " + node.type

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
    template = "<" + node.template + ">" if node.template else ""
    constants = [self.INDENT + m for m in node.constants]
    if node.methods:
      # We have multiple methods, and every method has multiple signatures
      # (i.e., the method string will have multiple lines). Combine this into
      # an array that contains all the lines, then indent the result.
      all_lines = sum((m.splitlines() for m in node.methods), [])
      methods = [self.INDENT + m for m in all_lines]
    else:
      methods = [self.INDENT + "pass"]
    header = "class " + node.name + template + parents + ":"
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
    ret = " -> " + node.return_type if node.return_type else ""
    exc = " raises " + ", ".join(node.exceptions) if node.exceptions else ""
    optional = ["..."] if node.has_optional else []
    return "(" + ", ".join(node.params + optional) + ")" + ret + exc

  def VisitParameter(self, node):
    """Convert a template parameter to a string."""
    return node.name + ": " + node.type

  def VisitTemplateItem(self, node):
    # TODO: implement
    return node

  def VisitBasicType(self, node):
    """Convert a type to a string."""
    return node.containing_type

  def VisitHomogeneousContainerType(self, node):
    """Convert a homogeneous container type to a string."""
    return node.base_type + "<" + node.element_type + ">"

  def VisitGenericType(self, node):
    """Convert a generic type (E.g. list<int>) to a string."""
    return node.base_type + "<" + ", ".join(p for p in node.parameters) + ">"

  def VisitUnionType(self, node):
    """Convert a union type ("x or y") to a string."""
    # TODO: insert parentheses if necessary (i.e., if the parent is
    # an intersection.)
    return " or ".join(node.type_list)

  def VisitIntersectionType(self, node):
    """Convert an intersection type ("x and y") to a string."""
    return " and ".join(node.type_list)

