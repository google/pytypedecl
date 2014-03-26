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
from pytypedecl.parse import ast
from pytypedecl.parse import parser
from pytypedecl.parse import typed_tuple
from pytypedecl.parse import typing


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
    expect = ast.TypeDeclUnit(
        interfacedefs=[],
        classdefs=[],
        funcdefs=[
            ast.Function(
                name="foo",
                params=[
                    ast.Parameter(
                        name="a",
                        type=typing.BasicType("int")),
                    ast.Parameter(
                        name="c",
                        type=typing.BasicType("bool"))],
                return_type=typing.BasicType("int"),
                template=[], provenance="", signature=None,
                exceptions=[
                    ast.ExceptionDef(typing.BasicType("Test")),
                    ast.ExceptionDef(typing.BasicType("Foo"))])])
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
    expect = ast.TypeDeclUnit(
        interfacedefs=[],
        classdefs=[],
        funcdefs=[
            ast.Function(
                name="foo",
                params=[
                    ast.Parameter(
                        name="a",
                        type=typing.BasicType("int")),
                    ast.Parameter(
                        name="c",
                        type=typing.BasicType("bool"))],
                return_type=typing.BasicType("int"),
                template=[], provenance="", signature=None,
                exceptions=[
                    ast.ExceptionDef(typing.BasicType("Test")),
                    ast.ExceptionDef(typing.BasicType("Foo"))]),
            ast.Function(
                name="foo",
                params=[],
                return_type=typing.BasicType(
                    "None"),
                template=[], provenance="", signature=None,
                exceptions=[]),
            ast.Function(
                name="add",
                params=[
                    ast.Parameter(
                        name="x",
                        type=typing.BasicType(
                            "int")),
                    ast.Parameter(
                        name="y",
                        type=typing.BasicType(
                            "int"))],
                return_type=typing.BasicType(
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
    expect = ast.TypeDeclUnit(
        interfacedefs=[],
        classdefs=[],
        funcdefs=[
            ast.Function(
                name="foo",
                params=[
                    ast.Parameter(
                        name="a",
                        type=typing.NoneAbleType(
                            base_type=typing.BasicType(
                                "int"))),
                    ast.Parameter(
                        name="b",
                        type=typing.UnionType(
                            type_list=[
                                typing.BasicType("int"),
                                typing.BasicType("float"),
                                typing.BasicType("None")])),
                    ast.Parameter(
                        name="c",
                        type=typing.IntersectionType(
                            type_list=[
                                typing.BasicType("Foo"),
                                typing.BasicType("s.Bar"),
                                typing.BasicType("Zot")]))],
                return_type=typing.NoneAbleType(
                    base_type=typing.BasicType(
                        "int")),
                exceptions=[
                    ast.ExceptionDef(typing.BasicType("Bad"))],
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
    expect = ast.TypeDeclUnit(
        interfacedefs=[],
        classdefs=[],
        funcdefs=[
            ast.Function(
                name="foo",
                params=[
                  ast.Parameter(
                      name="a",
                      type=typing.UnionType(
                          type_list=[
                              typing.BasicType("Foo"),
                              typing.IntersectionType(
                                  type_list=[
                                      typing.BasicType("Bar"),
                                      typing.BasicType("Zot")])]))
                    ],
                return_type=typing.BasicType("None"),
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
    expect = ast.TypeDeclUnit(
        interfacedefs=[
            ast.Interface(
                name="Readable",
                parents=[], template=[],
                attrs=[ast.MinimalFunction("Open"),
                       ast.MinimalFunction("Read"),
                       ast.MinimalFunction("Close")])],
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
    expect = ast.TypeDeclUnit(
        interfacedefs=[
            ast.Interface(
                name="Openable",
                parents=[], template=[],
                attrs=[ast.MinimalFunction("Open")]),
            ast.Interface(
                name="Closable",
                parents=[], template=[],
                attrs=[ast.MinimalFunction("Close")]),
            ast.Interface(
                name="Readable", template=[],
                parents=["Openable", "Closable"],
                attrs=[ast.MinimalFunction("Read")]),
            ast.Interface(
                name="Writable", template=[],
                parents=["Openable", "Closable"],
                attrs=[ast.MinimalFunction("Write")])],
        classdefs=[],
        funcdefs=[
            ast.Function(
                name="foo",
                params=[],
                return_type=typing.BasicType("None"),
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
    expect = ast.TypeDeclUnit(
        interfacedefs=[],
        classdefs=[],
        funcdefs=[
            ast.Function(
                name="interface",
                params=[
                    ast.Parameter(name="abcde",
                                   type=typing.ConstType(value="xyz")),
                    ast.Parameter(name="foo",
                                   type=typing.ConstType(value='a"b')),
                    ast.Parameter(name="b",
                                   type=typing.ConstType(value=-1.0)),
                    ast.Parameter(name="c",
                                   type=typing.ConstType(value=666))],
                return_type=typing.BasicType("int"),
                exceptions=[],
                template=[], provenance="", signature=None)])
    self.assertEqual(expect, result)

  def testNoReturnType(self):
    """Test a parsing error (no return type)."""

    data1 = "def foo()"
    data2 = "def foo() -> None"

    result1 = self.parser.Parse(data1)
    result2 = self.parser.Parse(data2)
    expect = ast.TypeDeclUnit(
        interfacedefs=[],
        classdefs=[],
        funcdefs=[
            ast.Function(
                name="foo",
                params=[],
                return_type=typing.BasicType("None"),
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
    expect = ast.TypeDeclUnit(
        interfacedefs=[],
        classdefs=[ast.Class(
            name="MyClass",
            parents=[],
            funcs=[
                ast.Function(
                    name="f1",
                    params=[
                        ast.Parameter(
                            name="c",
                            type=ast.TemplateItem(
                                name="C",
                                within_type=typing.BasicType("Cbase"),
                                level=1))],
                    return_type=typing.BasicType("None"),
                    exceptions=[],
                    template=[],
                    provenance="",
                    signature=None),
                ast.Function(
                    name="f2",
                    params=[
                        ast.Parameter(
                            name="c",
                            type=ast.TemplateItem(
                                name="C",
                                within_type=typing.BasicType("Cbase"),
                                level=1)),
                        ast.Parameter(
                            name="t1",
                            type=ast.TemplateItem(
                                name="T",
                                within_type=typing.BasicType("object"),
                                level=0)),
                        ast.Parameter(
                            name="t2",
                            type=typing.GenericType2(
                                base_type=typing.BasicType("dict"),
                                type1=ast.TemplateItem(
                                        name='C',
                                        within_type=typing.BasicType('Cbase'),
                                        level=1),
                                type2=typing.UnionType([
                                    ast.TemplateItem(
                                        name='C',
                                        within_type=typing.BasicType('Cbase'),
                                        level=1),
                                    ast.TemplateItem(
                                        name='T',
                                        within_type=typing.BasicType('object'),
                                        level=0),
                                    typing.BasicType('int')])))],
                    return_type=ast.TemplateItem(
                        name="T",
                        within_type=typing.BasicType("object"),
                        level=0),
                    exceptions=[
                        ast.ExceptionDef(
                            typing.GenericType1(
                                base_type=typing.BasicType("Error"),
                                type1=ast.TemplateItem(
                                    name="T",
                                    within_type=typing.BasicType("object"),
                                    level=0)))],
                    template=[
                        ast.TemplateItem(
                            name="T",
                            within_type=typing.BasicType("object"),
                            level=0),
                        ast.TemplateItem(
                            name="U",
                            within_type=typing.BasicType("object"),
                            level=0)],
                    provenance="",
                    signature=None)],
            template=[
                ast.TemplateItem(
                    name="C",
                    within_type=typing.BasicType("Cbase"),
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
