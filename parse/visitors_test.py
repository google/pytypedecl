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

  def testSuperClasses(self):
    src = textwrap.dedent("""
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
    """)
    tree = self.Parse(src)
    data = tree.Visit(visitors.ExtractSuperClasses())
    for base, superclass in ["CA", "DA", "DB", "EC", "ED", "EA"]:
      self.assertIn(superclass, data[base])

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

  @unittest.skip("TODO: Invalid tree: Signature not inside Function")
  def testPrintInvalidTree(self):
    """An actual example that Print to fail."""
    # The problem is Signature inside HomogeneousContainerType, but
    # Print only works if Signature is directly inside Function
    tree = pytd.TypeDeclUnit(
        constants=(), functions=(), modules={},
        classes=(
            pytd.Class(
                name="list", parents=(), constants=(), template=(),
                methods=(
                    pytd.Function(
                        name="__getitem__",
                        signatures=(
                            pytd.Signature(
                                params=(
                                    pytd.Parameter(
                                        name="self",
                                        type=pytd.HomogeneousContainerType(
                                            base_type=pytd.ClassType("list"),
                                            parameters=(
                                                pytd.Signature(
                                                    params=(),
                                                    return_type=pytd.UnknownType(),
                                                    exceptions=(),
                                                    template=(),
                                                    has_optional=True), ))
                                        ),
                                    pytd.Parameter(
                                        name="y",
                                        type=pytd.ClassType("~unknown3"))),
                                return_type=pytd.Signature(
                                    (), pytd.UnknownType(), (), (), True),
                                exceptions=(),
                                template=(),
                                has_optional=False), )
                        ), # end Function(__getitem__)
                    ),
                ), ))
    expect = textwrap.dedent("""\
        class list:
            def __getitem__(self: list<(...)>, y: `~unknown3`) -> (...)
    """)
    # remove trailing blanks on lines (dedent doesn't do it):
    expect = re.sub(r" +\n", "\n", expect).lstrip()
    printed = pytd.Print(tree)
    self.AssertSourceEquals(printed, expect)

  def testPrint(self):
    """Try every pytd class that can be generated from parser."""
    # TODO: node.modules
    # TODO: 'and' in type?
    # TODO: is 'def F() -> ?' is same as 'def F()'
    src = textwrap.dedent("""
      CONST1: int
      CONST2: int or float or Foo

      def Func()
      def FuncX() -> ?
      def Func2(a: int, b) raises AnException
      def Func3(a: str or float) -> ? raises Except1 or Except2
      def Func3<T>(a: int, b: T, c: list<T>) -> float or T or int
      def Func4<K extends int, V>(a: dict<K, V>) -> NoneType

      class C1<V, K extends str>(C2, C3, C4):
          def __init__(self: C1<V, K>) -> NoneType
          def Func4(k: K, v: V) -> K or V
    """)
    expect = textwrap.dedent("""
      CONST1: int
      CONST2: int or float or Foo

      def Func()
      def FuncX()
      def Func2(a: int, b) raises AnException
      def Func3(a: str or float) raises Except1 or Except2
      def Func3<T>(a: int, b: T, c: list<T>) -> float or T or int
      def Func4<K extends int, V>(a: dict<K, V>) -> NoneType

      class C1<V, K extends str>(C2, C3, C4):
          def __init__(self) -> NoneType
          def Func4(k: K, v: V) -> K or V
    """)
    # remove trailing blanks on lines (dedent doesn't do it):
    expect = re.sub(r" +\n", "\n", expect).lstrip()
    tree = self.Parse(src)
    printed = pytd.Print(tree)
    self.AssertSourceEquals(printed, expect)


if __name__ == "__main__":
  unittest.main()
