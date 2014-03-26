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


import collections
import textwrap
import unittest
from pytypedecl import pytd
from pytypedecl.parse import parser
from pytypedecl.parse import typed_tuple


class TestASTGeneration(unittest.TestCase):

  def setUp(self):
    self.parser = parser.PyParser()

  def testOneFunction(self):
    """Test parsing of a single function definition."""
    data = textwrap.dedent("""
        # a function def with two params
        def foo(a : int, c : bool) -> int raises Test, Foo
        """)

    result = self.parser.Parse(data)
    expect = pytd.TypeDeclUnit(
        constants=[],
        classes=[],
        functions=[
            pytd.Function(
                name="foo",
                signatures=[pytd.Signature(
                    params=[
                        pytd.Parameter(
                            name="a",
                            type=pytd.BasicType("int")),
                        pytd.Parameter(
                            name="c",
                            type=pytd.BasicType("bool"))],
                    return_type=pytd.BasicType("int"),
                    template=[], provenance="",
                    exceptions=[
                        pytd.ExceptionDef(pytd.BasicType("Test")),
                        pytd.ExceptionDef(pytd.BasicType("Foo"))])])])
    self.assertEqual(expect, result)

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
                      [p.type.containing_type
                       for p in f.signatures[0].params])

    f = result.Lookup("foo")
    self.assertEquals(len(f.signatures), 2)

    sig1, = [s for s in f.signatures if not s.params]
    self.assertEquals(sig1.return_type.containing_type, "None")
    sig2, = [s for s in f.signatures if len(s.params) == 2]
    self.assertEquals(sig2.return_type.containing_type, "int")
    self.assertEquals([p.type.containing_type for p in sig2.params],
                      ["int", "bool"])

  def testComplexFunction(self):
    """Test parsing of a function with unions, noneable etc."""

    data1 = textwrap.dedent("""
        def foo(a: int?, b: int or float or None, c: Foo and s.Bar and Zot) -> int? raises Bad
    """)
    data2 = textwrap.dedent("""
        def foo(a: int?, b: int or (float or None), c: Foo and (s.Bar and Zot)) -> int? raises Bad
    """)
    data3 = textwrap.dedent("""
        def foo(a: int?, b: (int or float) or None, c: (Foo and s.Bar) and Zot) -> int? raises Bad
    """)
    data4 = textwrap.dedent("""
        def foo(a: int?, b: ((((int or float)) or ((None)))), c: (((Foo) and s.Bar and (Zot)))) -> int? raises Bad
    """)

    result1 = self.parser.Parse(data1)
    result2 = self.parser.Parse(data2)
    result3 = self.parser.Parse(data3)
    result4 = self.parser.Parse(data4)
    expect = pytd.TypeDeclUnit(
        constants=[],
        classes=[],
        functions=[
            pytd.Function(
                name="foo",
                signatures=[pytd.Signature(
                    params=[
                        pytd.Parameter(
                            name="a",
                            type=pytd.NoneAbleType(
                                base_type=pytd.BasicType(
                                    "int"))),
                        pytd.Parameter(
                            name="b",
                            type=pytd.UnionType(
                                type_list=[
                                    pytd.BasicType("int"),
                                    pytd.BasicType("float"),
                                    pytd.BasicType("None")])),
                        pytd.Parameter(
                            name="c",
                            type=pytd.IntersectionType(
                                type_list=[
                                    pytd.BasicType("Foo"),
                                    pytd.BasicType("s.Bar"),
                                    pytd.BasicType("Zot")]))],
                    return_type=pytd.NoneAbleType(
                        base_type=pytd.BasicType(
                            "int")),
                    exceptions=[
                        pytd.ExceptionDef(pytd.BasicType("Bad"))],
                    template=[], provenance="")])])
    self.assertEqual(expect, result1)
    self.assertEqual(expect, result2)
    self.assertEqual(expect, result3)
    self.assertEqual(expect, result4)

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
                    params=[
                      pytd.Parameter(
                          name="a",
                          type=pytd.UnionType(
                              type_list=[
                                  pytd.BasicType("Foo"),
                                  pytd.IntersectionType(
                                      type_list=[
                                          pytd.BasicType("Bar"),
                                          pytd.BasicType("Zot")])]))
                        ],
                    return_type=pytd.BasicType("None"),
                    template=[], provenance="",
                    exceptions=[])])])
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
                    params=[
                        pytd.Parameter(name="abcde",
                                       type=pytd.ConstType(value="xyz")),
                        pytd.Parameter(name="foo",
                                       type=pytd.ConstType(value='a"b')),
                        pytd.Parameter(name="b",
                                       type=pytd.ConstType(value=-1.0)),
                        pytd.Parameter(name="c",
                                       type=pytd.ConstType(value=666))],
                    return_type=pytd.BasicType("int"),
                    exceptions=[],
                    template=[], provenance="")])])
    self.assertEqual(expect, result)

  def testNoReturnType(self):
    """Test a parsing error (no return type)."""

    data1 = "def foo()"
    data2 = "def foo() -> None"

    result1 = self.parser.Parse(data1)
    result2 = self.parser.Parse(data2)
    expect = pytd.TypeDeclUnit(
        constants=[],
        classes=[],
        functions=[
            pytd.Function(
                name="foo",
                signatures=[pytd.Signature(
                    params=[],
                    return_type=pytd.BasicType("None"),
                    template=[], provenance="", exceptions=[])])])
    self.assertEqual(result1, expect)
    self.assertEqual(result2, expect)
    self.assertEqual(result1, result2)  # redundant test
 
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


class C1(typed_tuple.Eq, collections.namedtuple("C1", ["a", "b"])):

  def Total(self):
    return sum(self)  # sum(tuple(self)) or sum(iter(self))

  def Total2(self):
    return self.a + self.b


class C2(typed_tuple.Eq, collections.namedtuple("C2", ["x", "y"])):
  pass


# class C2b has same fields as C2
class C2b(typed_tuple.Eq, collections.namedtuple("C2b", ["x", "y"])):
  pass


class TestTupleEq(unittest.TestCase):
  """Test typed_tupe.Eq (which is heavily used in other tests."""

  def testDeepEq1(self):
    c1a = C1(a=1, b=2)
    self.assertEqual(c1a.Total(), 3)
    self.assertEqual(c1a.Total2(), 3)
    c1b = C1(a=1, b=2)
    self.assertTrue(c1a == c1b)  # explicitly test __eq__
    self.assertFalse(c1a != c1b)  # explicitly test __ne__
    self.assertEqual(c1a, c1b)
    c2a = C2(x="foo", y=c1a)
    c2b = C2(x="foo", y=c1b)
    self.assertTrue(c2a == c2b)  # explicitly test __eq__
    self.assertFalse(c2a != c2b)  # explicitly test __ne__
    self.assertEqual(c1a, c1b)

  def testDeepEq2(self):
    c1a = C1(a=1, b=2)
    c1b = C1(a=1, b=3)
    self.assertFalse(c1a == c1b)  # explicitly test __eq__
    self.assertTrue(c1a != c1b)  # explicitly test __ne__
    self.assertNotEqual(c1a, c1b)
    c2a = C2(x="foo", y=c1a)
    c2b = C2(x="foo", y=c1b)
    self.assertFalse(c2a == c2b)  # explicitly test __eq__
    self.assertTrue(c2a != c2b)  # explicitly test __ne__
    self.assertNotEqual(c1a, c1b)

  def testImmutable(self):
    c1a = C1(a=1, b=2)
    c2a = C2(x="foo", y=c1a)
    c2b = C2b(x="foo", y=c1a)
    with self.assertRaises(AttributeError):
      c2a.x = "bar"
    with self.assertRaises(AttributeError):
      c2a.y.b = 999
    self.assertFalse(c2a == c2b)  # explicitly test __eq__
    self.assertTrue(c2a != c2b)  # explicitly test __ne__
    self.assertNotEqual(c2a, c2b)


if __name__ == "__main__":
  unittest.main()
