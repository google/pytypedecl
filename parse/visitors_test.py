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

  # TODO: node.modules
  # TODO: 'and' in type?
  # TODO: is 'def F() -> ?' is same as 'def F()'
  # TODO: BUG - printing of `C- 1`.__init__ doesn't match self's type properly
  _SRC1 = """
    `CONST-1`: `an-int`
    CONST2: int or float or Foo

    def `Func~`()
    def FuncX() -> ?
    def Func2(`a-1`: `an-int`, b) raises `An-Exception`
    def Func3(a: str or `a-float`, ...) -> ? raises Except1 or `Except-2`
    def func4<T>(AA: int, b: T, c: list<T>) -> float or T or NoneType
    def func5<K extends `an-int`, V>(a: `a-dict`<K, V>) -> NoneType

    class `C-1`<V, K extends `a-str`>(C2, C3, C4):
        def __init__(self: `C-1`<V, K>) -> NoneType
        def func6(k: K, v: V) -> K or V or NoneType
        def Func_7<Z>(self):
            self := `C-1`<K or NoneType>
  """

  _SRC2 = """
    def fib(n: `~unknown4`) -> `~unknown12`
    def fib(n: `~unknown4`) -> int
    def fib(n: `~unknown8`) -> int
    def fib(n: int) -> int

    class int:
        def __rsub__(self, y: `~unknown4`) -> int
        def __eq__(self, y: int) -> `~unknown10`
        def __eq__(self, y: int) -> bool
        def __radd__(self, y: `~unknown1`) -> int
        def __rmul__(self, y: `~unknown4`) -> int

    class `~unknown1`:
        def __add__(self, _1: int) -> `~unknown3`

    class `~unknown3`:
        pass

    class `~unknown4`:
        def __sub__(self, _1: int) -> `~unknown8`
        def __eq__(self, _1: int) -> `~unknown6`
        def __mul__(self, _1: int) -> `~unknown12`
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
      `CONST-1`: `an-int`
      CONST2: int or float or Foo

      def `Func~`()
      def FuncX()
      def Func2(`a-1`: `an-int`, b) raises `An-Exception`
      def Func3(a: str or `a-float`, ...) raises Except1 or `Except-2`
      def func4<T>(AA: int, b: T, c: list<T>) -> float or T or NoneType
      def func5<K extends `an-int`, V>(a: `a-dict`<K, V>) -> NoneType

      class `C-1`<V, K extends `a-str`>(C2, C3, C4):
          def __init__(self: `C-1`<V, K>) -> NoneType
          def func6(k: K, v: V) -> K or V or NoneType
          def Func_7<Z>(self: `C-1`<V, K>):
              self := `C-1`<K or NoneType>
    """
    src, expect, tree = self._PrepSrcExpect(self._SRC1, expect)
    printed = pytd.Print(tree)
    self.AssertSourceEquals(printed, expect)

  def testConstraints(self):
    expect = """
      constant('CONST-1', constant('CONST-1', ['an-int'-Var_an_int], named_type(Var_an_int))).
      constant('CONST2', constant('CONST2', ['Foo'-Var_Foo, 'float'-Var_float, 'int'-Var_int], union([named_type(Var_Foo), named_type(Var_float), named_type(Var_int)]))).

      function('Func~', function('Func~', [], [], [], no_optional, '?', no_raises, [])).
      function('FuncX', function('FuncX', [], [], [], no_optional, '?', no_raises, [])).
      function('Func2', function('Func2', [], ['An-Exception'-Var_An_Exception, 'an-int'-Var_an_int, 'object'-Var_object], [param('a-1', named_type(Var_an_int)), param('b', named_type(Var_object))], no_optional, '?', named_type(Var_An_Exception), [])).
      function('Func3', function('Func3', [], ['Except-2'-Var_Except_2, 'Except1'-Var_Except1, 'a-float'-Var_a_float, 'str'-Var_str], [param('a', union([named_type(Var_a_float), named_type(Var_str)]))], optional, '?', union([named_type(Var_Except1), named_type(Var_Except_2)]), [])).
      function('func4', function('func4', [template(Var_T, named_type(Var_object))], ['NoneType'-Var_NoneType, 'float'-Var_float, 'int'-Var_int, 'list'-Var_list, 'object'-Var_object], [param('AA', named_type(Var_int)), param('b', Var_T), param('c', homogeneous(named_type(Var_list), Var_T))], no_optional, union([Var_T, named_type(Var_NoneType), named_type(Var_float)]), no_raises, [])).
      function('func5', function('func5', [template(Var_K, named_type(Var_an_int)), template(Var_V, named_type(Var_object))], ['NoneType'-Var_NoneType, 'a-dict'-Var_a_dict, 'an-int'-Var_an_int, 'object'-Var_object], [param('a', generic(named_type(Var_a_dict), [Var_K, Var_V]))], no_optional, named_type(Var_NoneType), no_raises, [])).

      class('C-1', class('C-1', [template(Var_V, named_type(Var_object)), template(Var_K, named_type(Var_a_str))], [named_type(Var_C2), named_type(Var_C3), named_type(Var_C4)], [],
          ['C-1'-Var_C_1, 'C2'-Var_C2, 'C3'-Var_C3, 'C4'-Var_C4, 'NoneType'-Var_NoneType, 'a-str'-Var_a_str, 'object'-Var_object],
          [function('__init__', function('__init__', [], ['C-1'-Var_C_1, 'NoneType'-Var_NoneType], [param('self', generic(named_type(Var_C_1), [Var_V, Var_K]))], no_optional, named_type(Var_NoneType), no_raises, [])),
           function('func6', function('func6', [], ['NoneType'-Var_NoneType], [param('k', Var_K), param('v', Var_V)], no_optional, union([Var_K, Var_V, named_type(Var_NoneType)]), no_raises, [])),
           function('Func_7', function('Func_7', [template(Var_Z, named_type(Var_object))], ['C-1'-Var_C_1, 'NoneType'-Var_NoneType, 'object'-Var_object], [param('self', generic(named_type(Var_C_1), [Var_V, Var_K]))], no_optional, '?', no_raises, [mutable(self, homogeneous(named_type(Var_C_1), union([Var_K, named_type(Var_NoneType)])))]))])).
    """
    src, expect, tree = self._PrepSrcExpect(self._SRC1, expect)

    self.maxDiff = None  # For assertMultiLineEqual
    constraints = pytd.PrologConstraints(tree, "").strip() + "\n"
    print >>sys.stderr, '========================'  # TODO: remove
    print >>sys.stderr, constraints
    print >>sys.stderr, '========================'  # TODO: remove
    self.assertMultiLineEqual(expect, constraints)

  @unittest.skip("TODO: make this work")
  def testConstraints2(self):
    expect = ""
    src, expect, tree = self._PrepSrcExpect(self._SRC2, expect)
    constraints = pytd.PrologConstraints(tree, "").strip() + "\n"
    print >>sys.stderr, '========================'  # TODO: remove
    print >>sys.stderr, pytd.Print(tree)
    print >>sys.stderr, '========================'  # TODO: remove
    print >>sys.stderr, '========================'  # TODO: remove
    print >>sys.stderr, constraints
    print >>sys.stderr, '========================'  # TODO: remove
    self.assertMultiLineEqual(expect, constraints)


if __name__ == "__main__":
  unittest.main()
