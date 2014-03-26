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
        def foo(a : int, c : bool) -> int raise Test, Foo
        """)

    result = self.parser.Parse(data)
    expect = pytd.TypeDeclUnit(
        interfacedefs=[],
        classdefs=[],
        funcdefs=[
            pytd.Function(
                name="foo",
                params=[
                    pytd.Parameter(
                        name="a",
                        type=pytd.BasicType("int")),
                    pytd.Parameter(
                        name="c",
                        type=pytd.BasicType("bool"))],
                return_type=pytd.BasicType("int"),
                template=[], provenance="", signature=None,
                exceptions=[
                    pytd.ExceptionDef(pytd.BasicType("Test")),
                    pytd.ExceptionDef(pytd.BasicType("Foo"))])])
    self.assertEqual(expect, result)

  def testMultiFunction(self):
    """Test parsing of multiple function defs including overloaded version."""

    data = textwrap.dedent("""
        # several function defs with different sigs
        def foo(a : int, c : bool) -> int raise Test, Foo
        def foo() -> None
        def add(x : int, y : int) -> int
        """)

    result = self.parser.Parse(data)
    expect = pytd.TypeDeclUnit(
        interfacedefs=[],
        classdefs=[],
        funcdefs=[
            pytd.Function(
                name="foo",
                params=[
                    pytd.Parameter(
                        name="a",
                        type=pytd.BasicType("int")),
                    pytd.Parameter(
                        name="c",
                        type=pytd.BasicType("bool"))],
                return_type=pytd.BasicType("int"),
                template=[], provenance="", signature=None,
                exceptions=[
                    pytd.ExceptionDef(pytd.BasicType("Test")),
                    pytd.ExceptionDef(pytd.BasicType("Foo"))]),
            pytd.Function(
                name="foo",
                params=[],
                return_type=pytd.BasicType(
                    "None"),
                template=[], provenance="", signature=None,
                exceptions=[]),
            pytd.Function(
                name="add",
                params=[
                    pytd.Parameter(
                        name="x",
                        type=pytd.BasicType(
                            "int")),
                    pytd.Parameter(
                        name="y",
                        type=pytd.BasicType(
                            "int"))],
                return_type=pytd.BasicType(
                    "int"),
                template=[], provenance="", signature=None,
                exceptions=[])])
    self.assertEqual(expect, result)

  def testComplexFunction(self):
    """Test parsing of a function with unions, noneable etc."""

    data1 = textwrap.dedent("""
        def foo(a: int?, b: int | float | None, c: Foo & s.Bar & Zot) -> int? raise Bad
    """)
    data2 = textwrap.dedent("""
        def foo(a: int?, b: int | (float | None), c: Foo & (s.Bar & Zot)) -> int? raise Bad
    """)
    data3 = textwrap.dedent("""
        def foo(a: int?, b: (int | float) | None, c: (Foo & s.Bar) & Zot) -> int? raise Bad
    """)
    data4 = textwrap.dedent("""
        def foo(a: int?, b: ((((int | float)) | ((None)))), c: (((Foo) & s.Bar & (Zot)))) -> int? raise Bad
    """)

    result1 = self.parser.Parse(data1)
    result2 = self.parser.Parse(data2)
    result3 = self.parser.Parse(data3)
    result4 = self.parser.Parse(data4)
    expect = pytd.TypeDeclUnit(
        interfacedefs=[],
        classdefs=[],
        funcdefs=[
            pytd.Function(
                name="foo",
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
                template=[], provenance="", signature=None)])
    self.assertEqual(expect, result1)
    self.assertEqual(expect, result2)
    self.assertEqual(expect, result3)
    self.assertEqual(expect, result4)

  def testComplexCombinedType(self):
    """Test parsing a type with both union and intersection."""

    data1 = r"def foo(a: Foo | Bar & Zot)"
    data2 = r"def foo(a: Foo | (Bar & Zot))"
    result1 = self.parser.Parse(data1)
    result2 = self.parser.Parse(data2)
    expect = pytd.TypeDeclUnit(
        interfacedefs=[],
        classdefs=[],
        funcdefs=[
            pytd.Function(
                name="foo",
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
                template=[], provenance="", signature=None,
                exceptions=[])])
    self.assertEqual(expect, result1)
    self.assertEqual(expect, result2)

  def testInterfaceSimple(self):
    """Test parsing of basic interface."""

    data = textwrap.dedent("""
        interface Readable:
          def Open
          def Read
          def Close
         """)

    result = self.parser.Parse(data)
    # TODO: Remove test for expect_repr, as it adds very little
    # value, assuming that the structure equality (using typed_tuple.Eq) works
    # properly.
    expect_repr = ("TypeDeclUnit(interfacedefs="
                   "[Interface(name='Readable', "
                   "parents=[], attrs=["
                   "MinimalFunction(name='Open'), "
                   "MinimalFunction(name='Read'), "
                   "MinimalFunction(name='Close')], "
                   "template=[])], "
                   "classdefs=[], "
                   "funcdefs=[])")
    expect = pytd.TypeDeclUnit(
        interfacedefs=[
            pytd.Interface(
                name="Readable",
                parents=[], template=[],
                attrs=[pytd.MinimalFunction("Open"),
                       pytd.MinimalFunction("Read"),
                       pytd.MinimalFunction("Close")])],
        classdefs=[],
        funcdefs=[])
    self.assertEqual(expect, result)
    self.assertEqual(expect_repr, repr(result))

  def testInterfaceComplex(self):
    """Test parsing of interfaces with parents."""

    data = textwrap.dedent("""
        def foo() -> None

        interface Openable:
          def Open

        interface Closable:
          def Close

        interface Readable(Openable, Closable):
          def Read

        interface Writable(Openable, Closable):
          def Write
        """)

    result = self.parser.Parse(data)
    expect = pytd.TypeDeclUnit(
        interfacedefs=[
            pytd.Interface(
                name="Openable",
                parents=[], template=[],
                attrs=[pytd.MinimalFunction("Open")]),
            pytd.Interface(
                name="Closable",
                parents=[], template=[],
                attrs=[pytd.MinimalFunction("Close")]),
            pytd.Interface(
                name="Readable", template=[],
                parents=["Openable", "Closable"],
                attrs=[pytd.MinimalFunction("Read")]),
            pytd.Interface(
                name="Writable", template=[],
                parents=["Openable", "Closable"],
                attrs=[pytd.MinimalFunction("Write")])],
        classdefs=[],
        funcdefs=[
            pytd.Function(
                name="foo",
                params=[],
                return_type=pytd.BasicType("None"),
                exceptions=[],
                template=[], provenance="", signature=None)])
    self.assertEqual(expect, result)

  def testTokens(self):
    """Test various token forms (int, float, n"...", etc.)."""
    # TODO: a test with '"' or "'" in a string
    data = textwrap.dedent("""
        # "interface" is a reserved word in annotation language
        def `interface`(abcde: "xyz", foo: 'a"b', b: -1.0, c: 666) -> int
        """)

    result = self.parser.Parse(data)
    expect = pytd.TypeDeclUnit(
        interfacedefs=[],
        classdefs=[],
        funcdefs=[
            pytd.Function(
                name="interface",
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
                template=[], provenance="", signature=None)])
    self.assertEqual(expect, result)

  def testNoReturnType(self):
    """Test a parsing error (no return type)."""

    data1 = "def foo()"
    data2 = "def foo() -> None"

    result1 = self.parser.Parse(data1)
    result2 = self.parser.Parse(data2)
    expect = pytd.TypeDeclUnit(
        interfacedefs=[],
        classdefs=[],
        funcdefs=[
            pytd.Function(
                name="foo",
                params=[],
                return_type=pytd.BasicType("None"),
                template=[], provenance="", signature=None, exceptions=[])])
    self.assertEqual(result1, expect)
    self.assertEqual(result2, expect)
    self.assertEqual(result1, result2)  # redundant test

  def testTemplates(self):
    """Test the template name lookup."""

    data = textwrap.dedent("""
        class [C <= Cbase] MyClass:
          def f1(c: C)
          def[T,U] f2(c: C, t1: T, t2: dict[C, C|T|int]) -> T raise Error[T]
        """)

    result = self.parser.Parse(data)
    expect = pytd.TypeDeclUnit(
        interfacedefs=[],
        classdefs=[pytd.Class(
            name="MyClass",
            parents=[],
            funcs=[
                pytd.Function(
                    name="f1",
                    params=[
                        pytd.Parameter(
                            name="c",
                            type=pytd.TemplateItem(
                                name="C",
                                within_type=pytd.BasicType("Cbase"),
                                level=1))],
                    return_type=pytd.BasicType("None"),
                    exceptions=[],
                    template=[],
                    provenance="",
                    signature=None),
                pytd.Function(
                    name="f2",
                    params=[
                        pytd.Parameter(
                            name="c",
                            type=pytd.TemplateItem(
                                name="C",
                                within_type=pytd.BasicType("Cbase"),
                                level=1)),
                        pytd.Parameter(
                            name="t1",
                            type=pytd.TemplateItem(
                                name="T",
                                within_type=pytd.BasicType("object"),
                                level=0)),
                        pytd.Parameter(
                            name="t2",
                            type=pytd.GenericType2(
                                base_type=pytd.BasicType("dict"),
                                type1=pytd.TemplateItem(
                                        name='C',
                                        within_type=pytd.BasicType('Cbase'),
                                        level=1),
                                type2=pytd.UnionType([
                                    pytd.TemplateItem(
                                        name='C',
                                        within_type=pytd.BasicType('Cbase'),
                                        level=1),
                                    pytd.TemplateItem(
                                        name='T',
                                        within_type=pytd.BasicType('object'),
                                        level=0),
                                    pytd.BasicType('int')])))],
                    return_type=pytd.TemplateItem(
                        name="T",
                        within_type=pytd.BasicType("object"),
                        level=0),
                    exceptions=[
                        pytd.ExceptionDef(
                            pytd.GenericType1(
                                base_type=pytd.BasicType("Error"),
                                type1=pytd.TemplateItem(
                                    name="T",
                                    within_type=pytd.BasicType("object"),
                                    level=0)))],
                    template=[
                        pytd.TemplateItem(
                            name="T",
                            within_type=pytd.BasicType("object"),
                            level=0),
                        pytd.TemplateItem(
                            name="U",
                            within_type=pytd.BasicType("object"),
                            level=0)],
                    provenance="",
                    signature=None)],
            template=[
                pytd.TemplateItem(
                    name="C",
                    within_type=pytd.BasicType("Cbase"),
                    level=0)])],
        funcdefs=[])
    self.assertEqual(expect, result)


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
