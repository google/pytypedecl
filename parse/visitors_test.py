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
                                                    has_optional=True),))
                                        ),
                                    pytd.Parameter(
                                        name="y",
                                        type=pytd.ClassType("~unknown3"))),
                                return_type=pytd.Signature(
                                    (), pytd.UnknownType(), (), (), True),
                                exceptions=(),
                                template=(),
                                has_optional=False),)
                        ),  # end Function(__getitem__)
                    ),
                ),))
    expect = textwrap.dedent("""\
        class list:
            def __getitem__(self: list<(...)>, y: `~unknown3`) -> (...)
    """)
    # remove trailing blanks on lines (dedent doesn't do it):
    expect = re.sub(r" +\n", "\n", expect).lstrip()
    printed = pytd.Print(tree)
    self.AssertSourceEquals(printed, expect)

  # TODO: node.modules
  # TODO: 'and' in type?
  # TODO: is 'def F() -> ?' is same as 'def F()'
  # TODO: BUG - printing of `C 1`.__init__ doesn't match self's type properly
  _SRC1 = """
    `CONST 1`: `an int`
    CONST2: int or float or Foo

    def `Func `()
    def FuncX() -> ?
    def Func2(`a 1`: `an int`, b) raises `An Exception`
    def Func3(a: str or `a float`, ...) -> ? raises Except1 or `Except 2`
    def func4<T>(AA: int, b: T, c: list<T>) -> float or T or NoneType
    def func5<K extends `an int`, V>(a: `a dict`<K, V>) -> NoneType

    class `C 1`<V, K extends `a str`>(C2, C3, C4):
        def __init__(self: `C 1`<V, K>) -> NoneType
        def func6(k: K, v: V) -> K or V or NoneType
        def Func_7<Z>(self):
            self := `C 1`<K or NoneType>
  """

  def _PrepSrcExpect(self, src, expect):
    src = textwrap.dedent(src)
    expect = textwrap.dedent(expect)
    # remove trailing blanks on lines (dedent doesn't do it):
    expect = re.sub(r" +\n", "\n", expect).strip() + "\n"
    tree = self.Parse(src)
    return src, expect, tree

  def testPrint(self):
    """Try every pytd class that can be generated from parser."""
    expect = """
      `CONST 1`: `an int`
      CONST2: int or float or Foo

      def `Func `()
      def FuncX()
      def Func2(`a 1`: `an int`, b) raises `An Exception`
      def Func3(a: str or `a float`, ...) raises Except1 or `Except 2`
      def func4<T>(AA: int, b: T, c: list<T>) -> float or T or NoneType
      def func5<K extends `an int`, V>(a: `a dict`<K, V>) -> NoneType

      class `C 1`<V, K extends `a str`>(C2, C3, C4):
          def __init__(self: `C 1`<V, K>) -> NoneType
          def func6(k: K, v: V) -> K or V or NoneType
          def Func_7<Z>(self: `C 1`<V, K>):
              self := `C 1`<K or NoneType>
    """
    src, expect, tree = self._PrepSrcExpect(self._SRC1, expect)
    printed = pytd.Print(tree)
    self.AssertSourceEquals(printed, expect)

  def testConstraints(self):
    expect = """
      constant_type('CONST 1', named_type('an int')).
      constant_type('CONST2', union([named_type('Foo'), named_type('float'), named_type('int')])).

      function('Func ', [], [], no_optional, '?', no_raises, []).
      function('FuncX', [], [], no_optional, '?', no_raises, []).
      function('Func2', [], [param('a 1', named_type('an int')), param('b', object)], no_optional, '?', named_type('An Exception'), []).
      function('Func3', [], [param('a', union([named_type('a float'), named_type('str')]))], optional, '?', union([named_type('Except 2'), named_type('Except1')]), []).
      function('func4', [template(Var_T, object)], [param('AA', named_type('int')), param('b', Var_T), param('c', homogeneous(named_type('list'), Var_T))], no_optional, union([Var_T, named_type('NoneType'), named_type('float')]), no_raises, []).
      function('func5', [template(Var_K, named_type('an int')), template(Var_V, object)], [param('a', generic(named_type('a dict'), [Var_K, Var_V]))], no_optional, named_type('NoneType'), no_raises, []).

      class('C 1', [template(Var_V, object), template(Var_K, named_type('a str'))], [named_type('C2'), named_type('C3'), named_type('C4')], [],
          [function('__init__', [], [param('self', generic(named_type('C 1'), [Var_V, Var_K]))], no_optional, named_type('NoneType'), no_raises, []),
           function('func6', [], [param('k', Var_K), param('v', Var_V)], no_optional, union([Var_K, Var_V, named_type('NoneType')]), no_raises, []),
           function('Func_7', [template(Var_Z, object)], [param('self', generic(named_type('C 1'), [Var_V, Var_K]))], no_optional, '?', no_raises, [mutable(self, homogeneous(named_type('C 1'), union([Var_K, named_type('NoneType')])))])]).
    """
    src, expect, tree = self._PrepSrcExpect(self._SRC1, expect)

    self.maxDiff = None  # For assertMultiLineEqual
    constraints = tree.Visit(
        visitors.PrologConstraintsVisitor()).strip() + "\n"
    self.assertMultiLineEqual(expect, constraints)


if __name__ == "__main__":
  unittest.main()
