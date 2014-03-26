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
from pytypedecl import pytd
from tests import generics


class TestCheckerGenerics(unittest.TestCase):

  def testSimpleList(self):
    """Type checking of a list of int."""

    # should work with no exceptions
    self.assertEquals(3, generics.Length([1, 2, 3]))

    with self.assertRaises(checker.CheckTypeAnnotationError) as context:
      generics.Length([1, "42"])

    expected = checker.ParamTypeErrorMsg("Length",
                                         "l",
                                         list,
                                         pytd.GenericType1(list, int))
    [actual] = context.exception.args[0]
    self.assertEquals(expected, actual)

    with self.assertRaises(checker.CheckTypeAnnotationError) as context:
      generics.Length([1, "abc", 3])

    expected = checker.ParamTypeErrorMsg("Length",
                                         "l",
                                         list,
                                         pytd.GenericType1(list, int))

    [actual] = context.exception.args[0]
    self.assertEquals(expected, actual)

  def testUserContainerClass(self):
    """Type checking of a container class."""

    self.assertEquals(1, generics.UnwrapBox(generics.Box(1)))

    with self.assertRaises(checker.CheckTypeAnnotationError) as context:
      generics.UnwrapBox(generics.Box("hello"))

    expected_p = checker.ParamTypeErrorMsg("UnwrapBox",
                                           "b",
                                           generics.Box,
                                           pytd.GenericType1(
                                               generics.Box, int))

    expected_r = checker.ReturnTypeErrorMsg("UnwrapBox",
                                            str,
                                            int)

    [actual_p, actual_r] = context.exception.args[0]
    self.assertEquals(expected_p, actual_p)
    self.assertEquals(expected_r, actual_r)

  def testDict(self):
    """Type checking of built-in dict."""
    cache = {"Albert": 1, "Greg": 2, "Peter": 3}

    self.assertEquals(1, generics.FindInCache(cache, "Albert"))

    with self.assertRaises(checker.CheckTypeAnnotationError) as context:
      generics.FindInCache(cache, 9999)

    expected_p = checker.ParamTypeErrorMsg("FindInCache",
                                           "k",
                                           int,
                                           str)

    [actual_p, _] = context.exception.args[0]
    self.assertEquals(expected_p, actual_p)

  def testGenSimple(self):
    """Type checking of typed generator."""

    self.assertEquals([1, 2], generics.ConvertGenToList(
        e for e in [1, 2]))

    gen = generics._BadGen()
    with self.assertRaises(checker.CheckTypeAnnotationError) as context:
      generics.ConvertGenToList(gen)

    expected = checker.GeneratorGenericTypeErrorMsg("ConvertGenToList",
                                                    gen,
                                                    3,
                                                    float,
                                                    int)

    [gen_error] = context.exception.args[0]
    self.assertEquals(expected, gen_error)

  def testSameGenAsTwoArgs(self):
    """Passing same generator twice."""

    gen = (e for e in [1, 2, 3, 4, 5, 6])
    self.assertEquals([], generics.ConsumeDoubleGenerator(gen, gen))

    gen_broken = (e for e in [1, 2, 3, 4, 5, "6"])
    with self.assertRaises(checker.CheckTypeAnnotationError) as context:
      generics.ConsumeDoubleGenerator(gen_broken, gen_broken)

    expected = checker.GeneratorGenericTypeErrorMsg("ConsumeDoubleGenerator",
                                                    gen_broken,
                                                    6,
                                                    str,
                                                    int)
    [gen_error] = context.exception.args[0]
    self.assertEquals(expected, gen_error)


if __name__ == "__main__":
  unittest.main()
