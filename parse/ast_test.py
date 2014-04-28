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
from pytypedecl.parse import decorate
from pytypedecl.parse import node
from pytypedecl.parse import parser


class TestASTGeneration(unittest.TestCase):

  def setUp(self):
    self.parser = parser.PyParser()

  def TestRoundTrip(self, src, old_src=None):
    """Compile a string, and convert the result back to a string. Compare."""
    tree = self.parser.Parse(src)
    new_src = pytd.Print(tree)
    self.assertEquals((old_src or src).strip(), new_src.strip())

  def testOneFunction(self):
    """Test parsing of a single function definition."""
    # a function def with two params
    src = textwrap.dedent("""
        def foo(a: int, c: bool) -> int raises Foo, Test
        """)
    self.TestRoundTrip(src)

  def testOnlyOptional(self):
    """Test parsing of optional parameters"""
    src = textwrap.dedent("""
        def foo(...) -> int
    """).strip()
    self.TestRoundTrip(src)

  def testOptional1(self):
    """Test parsing of optional parameters"""
    src = textwrap.dedent("""
        def foo(a: int, ...) -> int
    """).strip()
    self.TestRoundTrip(src)

  def testOptional2(self):
    """Test parsing of optional parameters"""
    src = textwrap.dedent("""
        def foo(a: int, c: bool, ...) -> int
    """).strip()
    self.TestRoundTrip(src)

  def testOptionalWithSpaces(self):
    """Test parsing of ... with spaces."""
    # Python supports this, so we do, too.
    self.TestRoundTrip("def foo(a: int, c: bool, . . .) -> int",
                       "def foo(a: int, c: bool, ...) -> int")

  def testConstants(self):
    """Test parsing of constants"""
    src = textwrap.dedent("""
      a: int
      b: int or float
    """).strip()
    self.TestRoundTrip(src)

  def testTemplateReturn(self):
    src = textwrap.dedent("""
        def foo(a: int or float, c: bool) -> list<int> raises Foo, Test
    """)
    self.TestRoundTrip(src)

  def testMultiFunction(self):
    """Test parsing of multiple function defs including overloaded version."""

    data = textwrap.dedent("""
        # several function defs with different sigs
        def foo(a : int, c : bool) -> int raises Test, Foo
        def foo() -> None
        def add(x : int, y : int) -> int
        """)

    result = self.parser.Parse(data)

    f = result.Lookup("add")
    self.assertEquals(len(f.signatures), 1)
    self.assertEquals(["int", "int"],
                      [p.type.name
                       for p in f.signatures[0].params])

    f = result.Lookup("foo")
    self.assertEquals(len(f.signatures), 2)

    sig1, = [s for s in f.signatures if not s.params]
    self.assertEquals(sig1.return_type.name, "None")
    sig2, = [s for s in f.signatures if len(s.params) == 2]
    self.assertEquals(sig2.return_type.name, "int")
    self.assertEquals([p.type.name for p in sig2.params],
                      ["int", "bool"])

  def testComplexFunction(self):
    """Test parsing of a function with unions, noneable etc."""

    canonical = textwrap.dedent("""
        def foo(a: int, b: int or float or None, c: Foo and `s.Bar` and Zot) -> int raises Bad
    """)
    data1 = textwrap.dedent("""
        def foo(a: int, b: int or float or None, c: Foo and s.Bar and Zot) -> int raises Bad
    """)
    data2 = textwrap.dedent("""
        def foo(a: int, b: int or (float or None), c: Foo and (s.Bar and Zot)) -> int raises Bad
    """)
    data3 = textwrap.dedent("""
        def foo(a: int, b: (int or float) or None, c: (Foo and s.Bar) and Zot) -> int raises Bad
    """)
    data4 = textwrap.dedent("""
        def foo(a: int, b: ((((int or float)) or ((None)))), c: (((Foo) and s.Bar and (Zot)))) -> int raises Bad
    """)

    self.TestRoundTrip(data1, canonical)
    self.TestRoundTrip(data2, canonical)
    self.TestRoundTrip(data3, canonical)
    self.TestRoundTrip(data4, canonical)

  def testComplexCombinedType(self):
    """Test parsing a type with both union and intersection."""

    data1 = r"def foo(a: Foo or Bar and Zot)"
    data2 = r"def foo(a: Foo or (Bar and Zot))"
    result1 = self.parser.Parse(data1)
    result2 = self.parser.Parse(data2)
    expect = pytd.TypeDeclUnit(
        constants=[],
        classes=[],
        functions=[
            pytd.Function(
                name="foo",
                signatures=[pytd.Signature(
                    params=(
                        pytd.Parameter(
                            name="a",
                            type=pytd.UnionType(
                                type_list=(
                                    pytd.NamedType("Foo"),
                                    pytd.IntersectionType(
                                        type_list=(
                                            pytd.NamedType("Bar"),
                                            pytd.NamedType("Zot"))))
                            )
                        ),),
                    return_type=pytd.NamedType("object"),
                    template=(), has_optional=False, provenance="",
                    exceptions=())])],
        modules={})
    self.assertEqual(expect, result1)
    self.assertEqual(expect, result2)

  def testTokens(self):
    """Test various token forms (int, float, n"...", etc.)."""
    # TODO: a test with '"' or "'" in a string
    data = textwrap.dedent("""
        def `interface`(abcde: "xyz", foo: 'a"b', b: -1.0, c: 666) -> int
        """)

    result = self.parser.Parse(data)
    expect = pytd.TypeDeclUnit(
        constants=[],
        classes=[],
        functions=[
            pytd.Function(
                name="interface",
                signatures=[pytd.Signature(
                    params=(
                        pytd.Parameter(name="abcde",
                                       type=pytd.Scalar(value="xyz")),
                        pytd.Parameter(name="foo",
                                       type=pytd.Scalar(value='a"b')),
                        pytd.Parameter(name="b",
                                       type=pytd.Scalar(value=-1.0)),
                        pytd.Parameter(name="c",
                                       type=pytd.Scalar(value=666)),),
                    return_type=pytd.NamedType("int"),
                    exceptions=(),
                    template=(), has_optional=False, provenance="")])],
        modules={})
    self.assertEqual(expect, result)

  def testNoReturnType(self):
    """Test a parsing error (no return type)."""

    data1 = "def foo()"
    data2 = "def foo() -> None"

    self.TestRoundTrip(data1)
    self.TestRoundTrip(data2)
 
  def testTemplates(self):
    """Test template parsing."""

    return  # TODO: re-enable this test

    data = textwrap.dedent("""
        class<C extends Cbase> MyClass:
          def f1(p1: C)
          def<T,U> f2(p1: C, p2: T, p3: dict<C, C or T or int>) -> T raises Error<T>
        """)

    result = self.parser.Parse(data)
    myclass = result.Lookup("MyClass")
    self.assertEquals({t.name for t in myclass.template}, {"C"})

    f1 = myclass.Lookup("f1").signatures[0]
    param = f1.params[0]
    self.assertEquals(param.name, "p1")
    self.assertIsInstance(param.type, pytd.TemplateItem)
    template = param.type
    self.assertEquals(str(template.within_type), "Cbase")

    f2 = myclass.Lookup("f2").signatures[0]
    self.assertEquals([p.name for p in f2.params], ["p1", "p2", "p3"])
    self.assertEquals({t.name for t in f2.template}, {"T", "U"})
    p1, p2, p3 = f2.params
    t1, t2, t3 = p1.type, p2.type, p3.type
    self.assertIsInstance(t1, pytd.TemplateItem)
    self.assertIsInstance(t2, pytd.TemplateItem)
    self.assertNotIsInstance(t3, pytd.TemplateItem)
    self.assertEquals(str(t1.within_type), "Cbase")
    self.assertEquals(str(t2.within_type), "object")
    self.assertEquals(str(t3.base_type), "dict")
    self.assertIsInstance(f2.return_type, pytd.TemplateItem)
    self.assertEquals(f2.return_type.name, "T")
    self.assertEquals(len(f2.exceptions), 1)
    self.assertEquals(len(f2.template), 2)


class Node1(node.Node("a", "b")):
  def Total(self):
    return sum(self)  # sum(tuple(self)) or sum(iter(self))

  def Total2(self):
    return self.a + self.b


class Node2(node.Node("x", "y")):
  pass


# class Node2b has same fields as Node2
class Node2b(node.Node("x", "y")):
  pass


class Data(node.Node("d1", "d2", "d3")):
  pass


class V(node.Node("x")):
  pass


class X(node.Node("a", "b")):
  pass


class Y(node.Node("c", "d")):
  pass


class XY(node.Node("x", "y")):
  pass


class Visitor1(object):
  def VisitData(self, node):
    return node.Replace(d3=-1)


class Visitor2(object):
  def VisitData(self, node, r):
    return XY(r, r)

  def VisitV(self, node, r):
    return X(V(r), V(r))

  def VisitY(self, node):
    # change Y to X
    return X(*node)


class TestTupleEq(unittest.TestCase):
  """Test typed_tupe.Eq (which is heavily used in other tests."""

  def testDeepEq1(self):
    c1a = Node1(a=1, b=2)
    self.assertEqual(c1a.Total(), 3)
    self.assertEqual(c1a.Total2(), 3)
    c1b = Node1(a=1, b=2)
    self.assertTrue(c1a == c1b)  # explicitly test __eq__
    self.assertFalse(c1a != c1b)  # explicitly test __ne__
    self.assertEqual(c1a, c1b)
    c2a = Node2(x="foo", y=c1a)
    c2b = Node2(x="foo", y=c1b)
    self.assertTrue(c2a == c2b)  # explicitly test __eq__
    self.assertFalse(c2a != c2b)  # explicitly test __ne__
    self.assertEqual(c1a, c1b)

  def testDeepEq2(self):
    c1a = Node1(a=1, b=2)
    c1b = Node1(a=1, b=3)
    self.assertFalse(c1a == c1b)  # explicitly test __eq__
    self.assertTrue(c1a != c1b)  # explicitly test __ne__
    self.assertNotEqual(c1a, c1b)
    c2a = Node2(x="foo", y=c1a)
    c2b = Node2(x="foo", y=c1b)
    self.assertFalse(c2a == c2b)  # explicitly test __eq__
    self.assertTrue(c2a != c2b)  # explicitly test __ne__
    self.assertNotEqual(c1a, c1b)

  def testImmutable(self):
    c1a = Node1(a=1, b=2)
    c2a = Node2(x="foo", y=c1a)
    c2b = Node2b(x="foo", y=c1a)
    with self.assertRaises(AttributeError):
      c2a.x = "bar"
    with self.assertRaises(AttributeError):
      c2a.y.b = 999
    self.assertFalse(c2a == c2b)  # explicitly test __eq__
    self.assertTrue(c2a != c2b)  # explicitly test __ne__
    self.assertNotEqual(c2a, c2b)

  def testVisitor1(self):
    data = Data(42, 43, 44)
    x = X(1, [1, 2])
    y = Y([V(1)], {"bla": data})
    xy = XY(x, y)
    xy_expected = "XY(X(1, [1, 2]), Y([V(1)], {'bla': Data(42, 43, 44)}))"
    self.assertEquals(repr(xy), xy_expected)
    v = Visitor1()
    new_xy = xy.Visit(v)
    self.assertEquals(repr(new_xy),
                      "XY(X(1, [1, 2]), Y([V(1)], {'bla': Data(42, 43, -1)}))")
    self.assertEquals(repr(xy), xy_expected) # check that xy is unchanged


  def testVisitor2(self):
    xy = XY(V(1), Data(1, 2, 3))
    xy_expected = "XY(V(1), Data(1, 2, 3))"
    self.assertEquals(repr(xy), xy_expected)
    v = Visitor2()
    new_xy = xy.Visit(v, 42)
    self.assertEquals(repr(new_xy), "XY(X(V(42), V(42)), XY(42, 42))")
    self.assertEquals(repr(xy), xy_expected) # check that xy is unchanged


  def testRecursion(self):
    y = Y(Y(1, 2), Y(3, Y(4, 5)))
    y_expected = "Y(Y(1, 2), Y(3, Y(4, 5)))"
    self.assertEquals(repr(y), y_expected)
    v = Visitor2()
    new_y = y.Visit(v)
    self.assertEquals(repr(new_y), y_expected.replace("Y", "X"))
    self.assertEquals(repr(y), y_expected) # check that original is unchanged


class TestDecorate(unittest.TestCase):
  """Test adding additional methods to nodes in a tree using decorate.py."""

  def test1(self):
    decorator = decorate.Decorator()

    # Change pytd.NamedType to also have a method called "test1"
    @decorator  # pylint: disable=unused-variable
    class NamedType(pytd.NamedType):
      def test1(self):
        pass

    # Change pytd.Scalar to also have a method called "test2"
    @decorator
    class Scalar(pytd.Scalar):
      def test2(self):
        pass

    tree = pytd.Scalar(pytd.NamedType("test"))
    tree = decorator.Visit(tree)
    # test that we now have the "test2" method on pytd.Scalar
    tree.test2()
    # test that we now have the "test1" method on pytd.NamedType
    tree.value.test1()


if __name__ == "__main__":
  unittest.main()
