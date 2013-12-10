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

  def testOneFuncDef(self):
    """Test parsing of a single function definition."""
    data = textwrap.dedent("""
        # a function def with two params
        def foo(a : int, c : bool) -> int raise Test, Foo
        """)

    result = self.parser.Parse(data)
    expect = ast.PyOptTypeDeclUnit(
        interfacedefs=ast.PyOptInterfaceDefs(list_interfacedef=[]),
        classdefs=ast.PyOptClassDefs(list_classdef=[]),
        funcdefs=ast.PyOptFuncDefs(
            list_funcdef=[
                ast.PyOptFuncDef(
                    name="foo",
                    params=[
                        ast.PyOptParam(
                            name="a",
                            type=typing.BasicType(
                                containing_type="int")),
                        ast.PyOptParam(
                            name="c",
                            type=typing.BasicType(containing_type="bool"))],
                    return_type=typing.BasicType(containing_type="int"),
                    where=[], provenance="", signature=None,
                    exceptions=[
                        ast.PyOptException(
                            name=typing.BasicType(containing_type="Test")),
                        ast.PyOptException(
                            name=typing.BasicType(
                                containing_type="Foo"))])]))
    self.assertEqual(expect, result)

  def testMultiFuncDef(self):
    """Test parsing of multiple function defs including overloaded version."""

    data = textwrap.dedent("""
        # several function defs with different sigs
        def foo(a : int, c : bool) -> int raise Test, Foo
        def foo() -> None
        def add(x : int, y : int) -> int
        """)

    result = self.parser.Parse(data)
    expect = ast.PyOptTypeDeclUnit(
        interfacedefs=ast.PyOptInterfaceDefs(list_interfacedef=[]),
        classdefs=ast.PyOptClassDefs(list_classdef=[]),
        funcdefs=ast.PyOptFuncDefs(
            list_funcdef=[ast.PyOptFuncDef(
                name="foo",
                params=[
                    ast.PyOptParam(
                        name="a",
                        type=typing.BasicType(containing_type="int")),
                    ast.PyOptParam(
                        name="c",
                        type=typing.BasicType(containing_type="bool"))],
                return_type=typing.BasicType(containing_type="int"),
                where=[], provenance="", signature=None,
                exceptions=[
                    ast.PyOptException(
                        name=typing.BasicType(containing_type="Test")),
                    ast.PyOptException(
                        name=typing.BasicType(containing_type="Foo"))]),
                          ast.PyOptFuncDef(
                              name="foo",
                              params=[],
                              return_type=typing.BasicType(
                                  containing_type="None"),
                              where=[], provenance="", signature=None,
                              exceptions=[]),
                          ast.PyOptFuncDef(
                              name="add",
                              params=[
                                  ast.PyOptParam(
                                      name="x",
                                      type=typing.BasicType(
                                          containing_type="int")),
                                  ast.PyOptParam(
                                      name="y",
                                      type=typing.BasicType(
                                          containing_type="int"))],
                              return_type=typing.BasicType(
                                  containing_type="int"),
                              where=[], provenance="", signature=None,
                              exceptions=[])]))
    self.assertEqual(expect, result)

  def testComplexFuncDef(self):
    """Test parsing of a function with unions, noneable etc."""

    data = textwrap.dedent("""
        def foo(a: int?, b: int | float | None, c: Foo & s.Bar) -> int? raise Bad
    """)

    result = self.parser.Parse(data)
    expect = ast.PyOptTypeDeclUnit(
        interfacedefs=ast.PyOptInterfaceDefs(
            list_interfacedef=[]),
        classdefs=ast.PyOptClassDefs(list_classdef=[]),
        funcdefs=ast.PyOptFuncDefs(
            list_funcdef=[ast.PyOptFuncDef(
                name="foo",
                params=[
                    ast.PyOptParam(
                        name="a",
                        type=typing.NoneAbleType(
                            base_type=typing.BasicType(
                                containing_type="int"))),
                    ast.PyOptParam(
                        name="b",
                        type=typing.UnionType(
                            type_list=[
                                typing.BasicType(containing_type="int"),
                                typing.BasicType(containing_type="float"),
                                typing.BasicType(containing_type="None")])),
                    ast.PyOptParam(
                        name="c",
                        type=typing.IntersectionType(
                            type_list=[
                                typing.BasicType(containing_type="Foo"),
                                typing.BasicType(containing_type="s.Bar")]))],
                return_type=typing.NoneAbleType(
                    base_type=typing.BasicType(
                        containing_type="int")),
                exceptions=[
                    ast.PyOptException(
                        name=typing.BasicType(
                            containing_type="Bad"))],
                where=[], provenance="", signature=None)]))
    self.assertEqual(expect, result)

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
    expect_repr = ("PyOptTypeDeclUnit(interfacedefs=PyOptInterfaceDefs("
                   "list_interfacedef=[PyOptInterfaceDef(name='Readable', "
                   "parents=[], attrs=['Open', 'Read', 'Close'])]), "
                   "classdefs=PyOptClassDefs(list_classdef=[]), "
                   "funcdefs=PyOptFuncDefs(list_funcdef=[]))")
    expect = ast.PyOptTypeDeclUnit(
        interfacedefs=ast.PyOptInterfaceDefs(
            list_interfacedef=[
                ast.PyOptInterfaceDef(
                    name="Readable",
                    parents=[],
                    attrs=["Open", "Read", "Close"])]),
        classdefs=ast.PyOptClassDefs(list_classdef=[]),
        funcdefs=ast.PyOptFuncDefs(list_funcdef=[]))
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
    expect = ast.PyOptTypeDeclUnit(
        interfacedefs=ast.PyOptInterfaceDefs(
            list_interfacedef=[
                ast.PyOptInterfaceDef(
                    name="Openable",
                    parents=[],
                    attrs=["Open"]),
                ast.PyOptInterfaceDef(
                    name="Closable",
                    parents=[],
                    attrs=["Close"]),
                ast.PyOptInterfaceDef(
                    name="Readable",
                    parents=["Openable", "Closable"],
                    attrs=["Read"]),
                ast.PyOptInterfaceDef(
                    name="Writable",
                    parents=["Openable", "Closable"],
                    attrs=["Write"])]),
        classdefs=ast.PyOptClassDefs(list_classdef=[]),
        funcdefs=ast.PyOptFuncDefs(list_funcdef=[
            ast.PyOptFuncDef(
                name="foo",
                params=[],
                return_type=typing.BasicType(containing_type="None"),
                exceptions=[],
                where=[], provenance="", signature=None)]))
    self.assertEqual(expect, result)

  def testTokens(self):
    """Test various token forms (int, float, n"...", etc.)."""
    # TODO: a test with '"' or "'" in a string
    data = textwrap.dedent("""
        # "interface" is a reserved word in annotation language
        def `interface`(abcde: "xyz", foo: 'a"b', b: -1.0, c: 666) -> int
        """)

    result = self.parser.Parse(data)
    expect = ast.PyOptTypeDeclUnit(
        interfacedefs=ast.PyOptInterfaceDefs(list_interfacedef=[]),
        classdefs=ast.PyOptClassDefs(list_classdef=[]),
        funcdefs=ast.PyOptFuncDefs(
            list_funcdef=[
                ast.PyOptFuncDef(
                    name="interface",
                    params=[
                        ast.PyOptParam(name="abcde",
                                       type=typing.ConstType(value="xyz")),
                        ast.PyOptParam(name="foo",
                                       type=typing.ConstType(value='a"b')),
                        ast.PyOptParam(name="b",
                                       type=typing.ConstType(value=-1.0)),
                        ast.PyOptParam(name="c",
                                       type=typing.ConstType(value=666))],
                    return_type=typing.BasicType(containing_type="int"),
                    exceptions=[],
                    where=[], provenance="", signature=None)]))
    self.assertEqual(expect, result)

  def testSyntaxErrorReturnType(self):
    """Test a parsing error (no return type)."""

    data = "def foo()"

    with self.assertRaises(SyntaxError):
      self.parser.Parse(data)


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
