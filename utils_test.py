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


import textwrap
import unittest
from pytypedecl import pytd
from pytypedecl import utils
from pytypedecl.parse import parser_test


class TestUtils(parser_test.ParserTest):
  """Test the visitors in optimize.py."""

  def testGetDataFileReturnsString(self):
    # smoke test, only checks that it doesn't throw and the result is a string
    self.assertIsInstance(utils.GetDataFile("builtins/errno.pytd"), str)

  def testUnpackUnion(self):
    """Test for UnpackUnion."""
    ast = self.Parse("""
      c1: int or float
      c2: int
      c3: list<int or float>""")
    c1 = ast.Lookup("c1").type
    c2 = ast.Lookup("c2").type
    c3 = ast.Lookup("c3").type
    self.assertItemsEqual(utils.UnpackUnion(c1), c1.type_list)
    self.assertItemsEqual(utils.UnpackUnion(c2), [c2])
    self.assertItemsEqual(utils.UnpackUnion(c3), [c3])

  def testConcat(self):
    """Test for concatenating two pytd ASTs."""
    ast1 = self.Parse("""
      c1: int

      def f1() -> int

      class Class1:
        pass
    """)
    ast2 = self.Parse("""
      c2: int

      def f2() -> int

      class Class2:
        pass
    """)
    expected = textwrap.dedent("""
      c1: int
      c2: int

      def f1() -> int
      def f2() -> int

      class Class1:
          pass

      class Class2:
          pass
    """)
    combined = utils.Concat(ast1, ast2)
    self.AssertSourceEquals(combined, expected)

  def testJoinTypes(self):
    """Test that JoinTypes() does recursive flattening."""
    n1, n2, n3, n4, n5, n6 = [pytd.NamedType("n%d" % i) for i in xrange(6)]
    # n1 or (n2 or (n3))
    nested1 = pytd.UnionType((n1, pytd.UnionType((n2, pytd.UnionType((n3,))))))
    # ((n4) or n5) or n6
    nested2 = pytd.UnionType((pytd.UnionType((pytd.UnionType((n4,)), n5)), n6))
    joined = utils.JoinTypes([nested1, nested2])
    self.assertEquals(joined.type_list,
                      (n1, n2, n3, n4, n5, n6))

  def testJoinSingleType(self):
    """Test that JoinTypes() returns single types as-is."""
    a = pytd.NamedType("a")
    self.assertEquals(utils.JoinTypes([a]), a)
    self.assertEquals(utils.JoinTypes([a, a]), a)

  def testJoinNothingType(self):
    """Test that JoinTypes() removes or collapses 'nothing'."""
    a = pytd.NamedType("a")
    nothing = pytd.NothingType()
    self.assertEquals(utils.JoinTypes([a, nothing]), a)
    self.assertEquals(utils.JoinTypes([nothing]), nothing)
    self.assertEquals(utils.JoinTypes([nothing, nothing]), nothing)

  def testJoinEmptyTypesToNothing(self):
    """Test that JoinTypes() simplifies empty unions to 'nothing'."""
    self.assertIsInstance(utils.JoinTypes([]), pytd.NothingType)

  def testJoinUnknownTypes(self):
    """Test that JoinTypes() simplifies unions containing '?'."""
    types = [pytd.UnknownType(), pytd.NamedType("a")]
    self.assertIsInstance(utils.JoinTypes(types), pytd.UnknownType)


if __name__ == "__main__":
  unittest.main()
