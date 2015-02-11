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
from pytypedecl import optimize
from pytypedecl import pytd
from pytypedecl.parse import parser_test
from pytypedecl.parse import visitors


class TestOptimize(parser_test.ParserTest):
  """Test the visitors in optimize.py."""

  def OptimizedString(self, data):
    tree = self.Parse(data)
    new_tree = optimize.Optimize(tree)
    return pytd.Print(new_tree)

  def AssertOptimizeEquals(self, src, new_src):
    self.AssertSourceEquals(self.OptimizedString(src), new_src)

  def testJoinTypes(self):
    """Test that JoinTypes() does recursive flattening."""
    n1, n2, n3, n4, n5, n6 = [pytd.NamedType("n%d" % i) for i in xrange(6)]
    # n1 or (n2 or (n3))
    nested1 = pytd.UnionType((n1, pytd.UnionType((n2, pytd.UnionType((n3,))))))
    # ((n4) or n5) or n6
    nested2 = pytd.UnionType((pytd.UnionType((pytd.UnionType((n4,)), n5)), n6))
    joined = optimize.JoinTypes([nested1, nested2])
    self.assertEquals(joined.type_list,
                      (n1, n2, n3, n4, n5, n6))

  def testOneFunction(self):
    src = """
        def foo(a: int, c: bool) -> int raises Foo, Test
    """
    self.AssertOptimizeEquals(src, src)

  def testFunctionDuplicate(self):
    src = """
        def foo(a: int, c: bool) -> int raises Foo, Test
        def foo(a: int, c: bool) -> int raises Foo, Test
    """
    new_src = """
        def foo(a: int, c: bool) -> int raises Foo, Test
    """
    self.AssertOptimizeEquals(src, new_src)

  def testComplexFunctionDuplicate(self):
    src = """
        def foo(a: int or float, c: bool) -> list<int> raises Foo, Test
        def foo(a: str, c: str) -> str
        def foo(a: int, ...) -> A or B raises E<str>
        def foo(a: int or float, c: bool) -> list<int> raises Foo, Test
        def foo(a: int, ...) -> A or B raises E<str>
    """
    new_src = """
        def foo(a: int or float, c: bool) -> list<int> raises Foo, Test
        def foo(a: str, c: str) -> str
        def foo(a: int, ...) -> A or B raises E<str>
    """
    self.AssertOptimizeEquals(src, new_src)

  def testCombineReturns(self):
    src = """
        def foo(a: int) -> int
        def foo(a: int) -> float
    """
    new_src = """
        def foo(a: int) -> int or float
    """
    self.AssertOptimizeEquals(src, new_src)

  def testCombineRedundantReturns(self):
    src = """
        def foo(a: int) -> int
        def foo(a: int) -> float
        def foo(a: int) -> int or float
    """
    new_src = """
        def foo(a: int) -> int or float
    """
    self.AssertOptimizeEquals(src, new_src)

  def testCombineUnionReturns(self):
    src = """
        def foo(a: int) -> int or float
        def bar(a: str) -> str
        def foo(a: int) -> str or unicode
    """
    new_src = """
        def foo(a: int) -> int or float or str or unicode
        def bar(a: str) -> str
    """
    self.AssertOptimizeEquals(src, new_src)

  def testCombineExceptions(self):
    src = """
        def foo(a: int) -> int raises ValueError
        def foo(a: int) -> int raises IndexError
        def foo(a: float) -> int raises IndexError
        def foo(a: int) -> int raises AttributeError
    """
    new_src = """
        def foo(a: int) -> int raises ValueError, IndexError, AttributeError
        def foo(a: float) -> int raises IndexError
    """
    self.AssertOptimizeEquals(src, new_src)

  def testMixedCombine(self):
    src = """
        def foo(a: int) -> int raises ValueError
        def foo(a: int) -> float raises ValueError
        def foo(a: int) -> int raises IndexError
    """
    new_src = """
        def foo(a: int) -> int or float raises ValueError, IndexError
    """
    self.AssertOptimizeEquals(src, new_src)

  def testLossy(self):
    # Lossy compression is hard to test, since we don't know to which degree
    # "compressible" items will be compressed. This test only checks that
    # non-compressible things stay the same.
    src = """
        def foo(a: A) -> B raises C
        def foo(a: D) -> E raises F
    """
    flags = optimize.OptimizeFlags(lossy=True, use_abcs=True, max_union=4)
    self.AssertSourceEquals(
        optimize.Optimize(self.Parse(src), flags),
        src)

  def testExpand(self):
    src = """
        def foo(a: A or B, z: X or Y, u: U) -> Z
    """
    new_src = """
        def foo(a: A, z: X, u: U) -> Z
        def foo(a: A, z: Y, u: U) -> Z
        def foo(a: B, z: X, u: U) -> Z
        def foo(a: B, z: Y, u: U) -> Z
    """
    self.AssertSourceEquals(
        self.ApplyVisitorToString(src, optimize.ExpandSignatures()),
        new_src)

  def testFactorize(self):
    src = """
        def foo(a: A) -> Z
        def foo(a: A, x: X) -> Z
        def foo(a: A, x: Y) -> Z
        def foo(a: B, x: X) -> Z
        def foo(a: B, x: Y) -> Z
        def foo(a: A, x: Z, ...) -> Z
    """
    new_src = """
        def foo(a: A) -> Z
        def foo(a: A or B, x: X or Y) -> Z
        def foo(a: A, x: Z, ...) -> Z
    """
    self.AssertSourceEquals(
        self.ApplyVisitorToString(src, optimize.Factorize()), new_src)

  def testOptionalArguments(self):
    src = """
        def foo(a: A, ...) -> Z
        def foo(a: A) -> Z
        def foo(a: A, b: B) -> Z
        def foo(a: A, b: B, ...) -> Z
        def foo() -> Z
    """
    expected = """
        def foo(a: A, ...) -> Z
        def foo() -> Z
    """
    new_src = self.ApplyVisitorToString(src, optimize.ApplyOptionalArguments())
    self.AssertSourceEquals(new_src, expected)

  def testSuperClasses(self):
    src = """
        def f(x: list or tuple, y: frozenset or set) -> int or float
        def g(x: dict or Mapping, y: complex or int) -> set or dict or tuple or Container
        def h(x)
    """
    expected = """
        def f(x: Sequence, y: Set) -> Real
        def g(x: Mapping, y: Complex) -> Container
        def h(x)
    """
    visitor = optimize.FindCommonSuperClasses(use_abcs=True)
    new_src = self.ApplyVisitorToString(src, visitor)
    self.AssertSourceEquals(new_src, expected)

  def testUserSuperClassHierarchy(self):
    class_data = """
        class AB:
          pass
        class EFG:
          pass
        class A(AB, EFG):
          pass
        class B(AB):
          pass
        class E(EFG, AB):
          pass
        class F(EFG):
          pass
        class G(EFG):
          pass
    """

    src = """
        def f(x: A or B, y: A, z: B) -> E or F or G
        def g(x: E or F or G or B) -> E or F
        def h(x)
    """ + class_data

    expected = """
        def f(x: AB, y: A, z: B) -> EFG
        def g(x) -> EFG
        def h(x)
    """ + class_data

    hierarchy = self.Parse(src).Visit(visitors.ExtractSuperClasses())
    visitor = optimize.FindCommonSuperClasses(hierarchy, use_abcs=False)
    new_src = self.ApplyVisitorToString(src, visitor)
    self.AssertSourceEquals(new_src, expected)

  def testShortenUnions(self):
    src = """
        def f(x: A or B or C or D) -> X
        def g(x: A or B or C or D or E) -> X
        def h(x: A or object) -> X
    """
    expected = """
        def f(x: A or B or C or D) -> X
        def g(x) -> X
        def h(x) -> X
    """
    new_src = self.ApplyVisitorToString(src,
                                        optimize.ShortenUnions(max_length=4))
    self.AssertSourceEquals(new_src, expected)

  def testCombineContainers(self):
    src = """
        def f(x: list<int> or list<float>)
        def g(x: list<int> or str or list<float> or set<int> or long)
        def h(x: list<int> or list<str> or set<int> or set<float>)
    """
    expected = """
        def f(x: list<int or float>)
        def g(x: list<int or float> or str or set<int> or long)
        def h(x: list<int or str> or set<int or float>)
    """
    new_src = self.ApplyVisitorToString(src,
                                        optimize.CombineContainers())
    self.AssertSourceEquals(new_src, expected)

  def testPullInMethodClasses(self):
    src = """
        class A:
          mymethod1: Method1
          mymethod2: Method2
          member: Method3
        class Method1:
          def __call__(self: A, x: int)
        class Method2:
          def __call__(self: ?, x: int)
        class Method3:
          def __call__(x: bool, y: int)
    """
    expected = """
        class A:
          member: Method3
          def mymethod1(self, x: int)
          def mymethod2(self, x: int)
        class Method3:
          def __call__(x: bool, y: int)
    """
    new_src = self.ApplyVisitorToString(src,
                                        optimize.PullInMethodClasses())
    self.AssertSourceEquals(new_src, expected)

if __name__ == "__main__":
  unittest.main()
