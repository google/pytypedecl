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


import re
import sys
import textwrap
import unittest

from pytypedecl import pytd
from pytypedecl.parse import parser_test
from pytypedecl.parse import visitors


# All of these tests implicitly test pytd.Print because
# parser_test.AssertSourceEquals() uses pytd.Print.


class TestVisitors(parser_test.ParserTest):
  """Tests the classes in parse/visitors."""

  def testLookupClasses(self):
    src = textwrap.dedent("""
        class object:
            pass

        class A:
            def a(self, a: A, b: B) -> A or B raises A, B

        class B:
            def b(self, a: A, b: B) -> A or B raises A, B
    """)
    tree = self.Parse(src)
    new_tree = visitors.LookupClasses(tree)
    self.AssertSourceEquals(new_tree, src)
    new_tree.Visit(visitors.VerifyLookup())

  def testMaybeFillInClasses(self):
    src = textwrap.dedent("""
        class A:
            def a(self, a: A, b: B) -> A or B raises A, B
    """)
    tree = self.Parse(src)
    ty_a = pytd.ClassType("A")
    visitors.FillInClasses(ty_a, tree)
    self.assertIsNotNone(ty_a.cls)
    ty_b = pytd.ClassType("B")
    visitors.FillInClasses(ty_b, tree)
    self.assertIsNone(ty_b.cls)

  def testReplaceTypes(self):
    src = textwrap.dedent("""
        class A:
            def a(self, a: A or B) -> A or B raises A, B
    """)
    expected = textwrap.dedent("""
        class A:
            def a(self: A2, a: A2 or B) -> A2 or B raises A2, B
    """)
    tree = self.Parse(src)
    new_tree = tree.Visit(visitors.ReplaceTypes({"A": pytd.NamedType("A2")}))
    self.AssertSourceEquals(new_tree, expected)

  def testSuperClassesByName(self):
    src = textwrap.dedent("""
      class A(nothing):
          pass
      class B(nothing):
          pass
      class C(A):
          pass
      class D(A,B):
          pass
      class E(C,D,A):
          pass
    """)
    tree = self.Parse(src)
    data = tree.Visit(visitors.ExtractSuperClassesByName())
    self.assertItemsEqual((), data["A"])
    self.assertItemsEqual((), data["B"])
    self.assertItemsEqual(("A",), data["C"])
    self.assertItemsEqual(("A", "B"), data["D"])
    self.assertItemsEqual(("A", "C", "D"), data["E"])

  def testSuperClasses(self):
    src = textwrap.dedent("""
      class A(nothing):
          pass
      class B(nothing):
          pass
      class C(A):
          pass
      class D(A,B):
          pass
      class E(C,D,A):
          pass
    """)
    ast = visitors.LookupClasses(self.Parse(src))
    data = ast.Visit(visitors.ExtractSuperClasses())
    self.assertItemsEqual([], [t.name for t in data[ast.Lookup("A")]])
    self.assertItemsEqual([], [t.name for t in data[ast.Lookup("B")]])
    self.assertItemsEqual(["A"], [t.name for t in data[ast.Lookup("C")]])
    self.assertItemsEqual(["A", "B"], [t.name for t in data[ast.Lookup("D")]])
    self.assertItemsEqual(["C", "D", "A"],
                          [t.name for t in data[ast.Lookup("E")]])

  def testInstantiateTemplates(self):
    src = textwrap.dedent("""
        def foo(x: int) -> A<int>

        class A<T>:
            def foo(a: T) -> T raises T
    """)
    expected = textwrap.dedent("""
        def foo(x: int) -> `A<int>`

        class `A<int>`:
            def foo(a: int) -> int raises int
    """)
    tree = self.Parse(src)
    new_tree = visitors.InstantiateTemplates(tree)
    self.AssertSourceEquals(new_tree, expected)

  def testInstantiateTemplatesWithParameters(self):
    src = textwrap.dedent("""
        def foo(x: int) -> T1<float, >
        def foo(x: int) -> T2<int, complex>

        class T1<A>:
            def foo(a: A) -> A raises A

        class T2<A, B>:
            def foo(a: A) -> B raises B
    """)
    expected = textwrap.dedent("""
        def foo(x: int) -> `T1<float, >`
        def foo(x: int) -> `T2<int, complex>`

        class `T1<float, >`:
            def foo(a: float) -> float raises float

        class `T2<int, complex>`:
            def foo(a: int) -> complex raises complex
    """)
    tree = self.Parse(src)
    new_tree = visitors.InstantiateTemplates(tree)
    self.AssertSourceEquals(new_tree, expected)

  def testStripSelf(self):
    src = textwrap.dedent("""
        def add(x: int, y: int) -> int
        class A:
            def bar(self, x: int) -> float
            def baz(self) -> float
            def foo(self, x: int, y: float) -> float
    """)
    expected = textwrap.dedent("""
        def add(x: int, y: int) -> int

        class A:
            def bar(x: int) -> float
            def baz() -> float
            def foo(x: int, y: float) -> float
    """)
    tree = self.Parse(src)
    new_tree = tree.Visit(visitors.StripSelf())
    self.AssertSourceEquals(new_tree, expected)


if __name__ == "__main__":
  unittest.main()
