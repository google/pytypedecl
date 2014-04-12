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


class TestOptimize(parser_test.ParserTest):
  """Test the visitors in optimize.py."""

  def OptimizedString(self, data):
    tree = self.parser.Parse(data)
    new_tree = optimize.Optimize(tree)
    return pytd.Print(new_tree)

  def AssertOptimizeEquals(self, src, new_src):
    self.AssertSourceEquals(self.OptimizedString(src), new_src)

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
        def foo(a: int) -> float or int
    """
    self.AssertOptimizeEquals(src, new_src)

  def testCombineExceptions(self):
    src = """
        def foo(a: int) -> int raises ValueError
        def foo(a: int) -> int raises IndexError
        def foo(a: float) -> int raises IndexError
    """
    new_src = """
        def foo(a: int) -> int raises IndexError, ValueError
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
        def foo(a: int) -> float or int raises IndexError, ValueError
    """
    self.AssertOptimizeEquals(src, new_src)

  def testSorting1(self):
    src = """
        def foo(a: int) -> c
        def foo(a: int) -> b
        def foo(a: int) -> a
        def foo(a: int) -> a
        def foo(a: int) -> d
    """
    new_src = """
        def foo(a: int) -> a or b or c or d
    """
    self.AssertOptimizeEquals(src, new_src)

  def testSorting2(self):
    src = """
        def foo(a: int) raises D
        def foo(a: int) raises B
        def foo(a: int) raises B
        def foo(a: int) raises A
        def foo(a: int) raises A
        def foo(a: int) raises C
    """
    new_src = """
        def foo(a: int) raises A, B, C, D
    """
    self.AssertOptimizeEquals(src, new_src)

  def testExpand(self):
    src = """
        def foo(a: A or B, x: X or Y) -> Z
    """
    new_src = """
        def foo(a: A, x: X) -> Z
        def foo(a: A, x: Y) -> Z
        def foo(a: B, x: X) -> Z
        def foo(a: B, x: Y) -> Z
    """
    self.AssertSourceEquals(
        self.ApplyVisitorToString(src, optimize.ExpandSignatures()),
        new_src)

if __name__ == "__main__":
  unittest.main()
