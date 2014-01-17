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
from pytypedecl import checker
from pytypedecl.parse import ast
from pytypedecl.parse import typing
from tests import interface


class TestCheckerInterface(unittest.TestCase):

  def testSimpleInterfaceAsArg(self):
    """Function expecting a type matching an Interface."""

    self.assertEquals("Hello", interface.ReadStuff(interface.FakeReadable()))

    with self.assertRaises(checker.CheckTypeAnnotationError) as context:
      interface.ReadStuff(interface.FakeOpenable())

    expected_p = checker.ParamTypeErrorMsg(
        "ReadStuff",
        "r",
        interface.FakeOpenable,
        typing.StructType([ast.PyOptFuncDefMinimal("Open"),
                           ast.PyOptFuncDefMinimal("Read"),
                           ast.PyOptFuncDefMinimal("Close")]))

    expected_e = checker.ExceptionTypeErrorMsg("ReadStuff",
                                               AttributeError,
                                               ())
    [actual_p, actual_e] = context.exception.args[0]
    self.assertEquals(expected_p, actual_p)
    self.assertEquals(expected_e, actual_e)

  # TODO: reinstate this test, probably with PyOptInterfaceDef
  def testReturnInterface(self):
    """Function returning an object matching an Interface.
    """

    with self.assertRaises(checker.CheckTypeAnnotationError) as context:
      interface.GetWritable()

    expected_r = checker.ReturnTypeErrorMsg(
        "GetWritable",
        interface.NoGoodWritable,
        typing.StructType([ast.PyOptFuncDefMinimal("Open"),
                           ast.PyOptFuncDefMinimal("Write"),
                           ast.PyOptFuncDefMinimal("Close")]))

    [actual_r] = context.exception.args[0]
    self.assertEquals(expected_r, actual_r)


if __name__ == "__main__":
  unittest.main()
