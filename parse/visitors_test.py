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


import unittest

from pytypedecl import pytd
from pytypedecl.parse import parser_test
from pytypedecl.parse import visitors


class VerifyLookup(object):
  """Utility class for testing visitors.LookupClasses."""

  def VisitNamedType(self, _):
    raise ValueError("All NamedType nodes should have been replaced.")

  def VisitClassType(self, node):
    if node.cls is None:
      raise ValueError("All ClassType nodes should have been resolved.")


class TestVisitors(parser_test.ParserTest):
  """Tests the classes in parse/visitors."""

  def testLookupClasses(self):
    src = """
        class object:
          pass
        class A:
          def a(self, a: A, b: B) -> A or B raises A, B
        class B:
          def b(self, a: A, b: B) -> A or B raises A, B
    """
    tree = self.Parse(src)
    new_tree = visitors.LookupClasses(tree)
    self.AssertSourceEquals(new_tree, src)
    new_tree.Visit(VerifyLookup())

  def testReplaceType(self):
    src = """
        class A:
          def a(self, a: A or B) -> A or B raises A, B
    """
    expected = """
        class A:
          def a(self, a: A2 or B) -> A2 or B raises A2, B
    """
    tree = self.Parse(src)
    new_tree = tree.Visit(visitors.ReplaceType({"A": pytd.NamedType("A2")}))
    self.AssertSourceEquals(new_tree, expected)

  def testSuperClasses(self):
    src = """
      class A:
        pass
      class B:
        pass
      class C(A):
        pass
      class D(A,B):
        pass
      class E(C,D,A):
        pass
    """
    tree = self.Parse(src)
    data = tree.Visit(visitors.ExtractSuperClasses())
    for base, superclass in ["CA", "DA", "DB", "EC", "ED", "EA"]:
      self.assertIn(superclass, data[base])

  def testInstantiateTemplates(self):
    src = """
        def foo(x: int) -> A<int>
        class<T> A:
          def foo(a: T) -> T raises T
    """
    expected = """
        def foo(x: int) -> `A<int>`
        class `A<int>`:
          def foo(a: int) -> int raises int
    """
    tree = self.Parse(src)
    new_tree = tree.Visit(visitors.InstantiateTemplates(tree))
    self.AssertSourceEquals(new_tree, expected)

  def testStripSelf(self):
    src = """
        def add(x: int, y: int) -> int
        class A:
          def bar(self, x: int) -> float
          def baz(self) -> float
          def foo(self, x: int, y: float) -> float
    """
    expected = """
        def add(x: int, y: int) -> int
        class A:
          def bar(x: int) -> float
          def baz() -> float
          def foo(x: int, y: float) -> float
    """
    tree = self.Parse(src)
    new_tree = tree.Visit(visitors.StripSelf())
    self.AssertSourceEquals(new_tree, expected)


if __name__ == "__main__":
  unittest.main()
