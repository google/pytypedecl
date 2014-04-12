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
from pytypedecl.parse import parser_test
from pytypedecl.parse import visitors


class TestVisitors(parser_test.ParserTest):
  """Tests the classes in parse/visitors."""

  def testInstantiateTemplates(self):
    src = """
        def foo(x: int) -> A<int>
        class<T> A:
          def foo(a: T) -> T raises T
    """
    expected = """
        def foo(x: int) -> A<int>
        class `A<int>`:
          def foo(a: int) -> int raises int
    """
    tree = self.parser.Parse(src)
    new_tree = tree.Visit(visitors.InstantiateTemplates(tree))
    new_src = new_tree.Visit(visitors.PrintVisitor())
    self.AssertSourceEquals(new_src, expected)

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
    tree = self.parser.Parse(src)
    new_tree = tree.Visit(visitors.StripSelf())
    new_src = new_tree.Visit(visitors.PrintVisitor())
    self.AssertSourceEquals(new_src, expected)


if __name__ == "__main__":
  unittest.main()
