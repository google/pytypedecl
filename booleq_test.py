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

"""Tests for booleq.py."""

import unittest

from pytypedecl import booleq

# pylint: disable=invalid-name
And = booleq.And
Or = booleq.Or
Eq = booleq.Eq


# TODO: a coworker wants me to remind him to create more tests for
#              booleq.py.


class TestBoolEq(unittest.TestCase):
  """Test algorithms and datastructures of booleq.py."""

  def testTrueAndFalse(self):
    self.assertNotEqual(booleq.TRUE, booleq.FALSE)
    self.assertNotEqual(booleq.FALSE, booleq.TRUE)
    self.assertEqual(booleq.TRUE, booleq.TRUE)
    self.assertEqual(booleq.FALSE, booleq.FALSE)

  def testEquality(self):
    self.assertEqual(booleq.Eq("a", "b"),
                     booleq.Eq("b", "a"))
    self.assertEqual(booleq.Eq("a", "b"),
                     booleq.Eq("a", "b"))
    self.assertNotEqual(booleq.Eq("a", "a"),
                        booleq.Eq("a", "b"))
    self.assertNotEqual(booleq.Eq("b", "a"),
                        booleq.Eq("b", "b"))

  def testAnd(self):
    self.assertEqual(booleq.TRUE,
                     booleq.And([]))
    self.assertEqual(booleq.TRUE,
                     booleq.And([booleq.TRUE]))
    self.assertEqual(booleq.TRUE,
                     booleq.And([booleq.TRUE, booleq.TRUE]))
    self.assertEqual(booleq.FALSE,
                     booleq.And([booleq.TRUE, booleq.FALSE]))
    self.assertEqual(booleq.Eq("a", "b"),
                     booleq.And([booleq.Eq("a", "b"),
                                 booleq.TRUE]))
    self.assertEqual(booleq.FALSE,
                     booleq.And([booleq.Eq("a", "b"),
                                 booleq.FALSE]))

  def testOr(self):
    self.assertEqual(booleq.FALSE,
                     booleq.Or([]))
    self.assertEqual(booleq.TRUE,
                     booleq.Or([booleq.TRUE]))
    self.assertEqual(booleq.TRUE,
                     booleq.Or([booleq.TRUE, booleq.TRUE]))
    self.assertEqual(booleq.TRUE,
                     booleq.Or([booleq.TRUE, booleq.FALSE]))
    self.assertEqual(booleq.Eq("a", "b"),
                     booleq.Or([booleq.Eq("a", "b"),
                                booleq.FALSE]))
    self.assertEqual(booleq.TRUE,
                     booleq.Or([booleq.Eq("a", "b"),
                                booleq.TRUE]))

  def testNestedEquals(self):
    eq1 = booleq.Eq("a", "u")
    eq2 = booleq.Eq("b", "v")
    eq3 = booleq.Eq("c", "w")
    eq4 = booleq.Eq("d", "x")
    nested = Or([And([eq1, eq2]), And([eq3, eq4])])
    self.assertEqual(nested, nested)

  def testOrder(self):
    eq1 = booleq.Eq("a", "b")
    eq2 = booleq.Eq("b", "c")
    self.assertEqual(booleq.Or([eq1, eq2]),
                     booleq.Or([eq2, eq1]))
    self.assertEqual(booleq.And([eq1, eq2]),
                     booleq.And([eq2, eq1]))

  def testHash(self):
    eq1 = booleq.Eq("a", "b")
    eq2 = booleq.Eq("b", "c")
    eq3 = booleq.Eq("c", "d")
    self.assertEqual(hash(booleq.Eq("x", "y")),
                     hash(booleq.Eq("y", "x")))
    self.assertEqual(hash(booleq.Or([eq1, eq2, eq3])),
                     hash(booleq.Or([eq2, eq3, eq1])))
    self.assertEqual(hash(booleq.And([eq1, eq2, eq3])),
                     hash(booleq.And([eq2, eq3, eq1])))

  def testPivots(self):
    # x == 0 || x == 1
    equation = Or([Eq("x", "0"), Eq("x", "1")])
    self.assertItemsEqual(["0", "1"], equation.extract_pivots()["x"])

    # x == 0 && x == 0
    equation = And([Eq("x", "0"), Eq("x", "0")])
    self.assertItemsEqual(["0"], equation.extract_pivots()["x"])

    # x == 0 && (x == 0 || x == 1)
    equation = And([Eq("x", "0"), Or([Eq("x", "0"), Eq("x", "1")])])
    self.assertItemsEqual(["0"], equation.extract_pivots()["x"])

    # x == 0 || x == 0
    equation = And([Eq("x", "0"), Eq("x", "0")])
    self.assertItemsEqual(["0"], equation.extract_pivots()["x"])

  def testSimplify(self):
    # x == 0 || x == 1  with x in {0}
    equation = Or([Eq("x", "0"), Eq("x", "1")])
    values = {"x": ["0"]}
    self.assertEquals(Eq("x", "0"), equation.simplify(values))

    # x == 0 || x == 1  with x in {0}
    equation = Or([Eq("x", "0"), Eq("x", "1")])
    values = {"x": ["0", "1"]}
    self.assertEquals(equation, equation.simplify(values))

    # x == 0 with x in {1}
    equation = Eq("x", "0")
    values = {"x": ["1"]}
    self.assertEquals(booleq.FALSE, equation.simplify(values))

    # x == 0 with x in {0}
    equation = Eq("x", "0")
    values = {"x": ["0"]}
    self.assertEquals(equation, equation.simplify(values))

    # x == 0 && y == 0 with x in {1}, y in {1}
    equation = Or([Eq("x", "0"), Eq("y", "1")])
    values = {"x": ["1"], "y": ["1"]}
    self.assertEquals(Eq("y", "1"), equation.simplify(values))

    # x == 0 && y == 0 with x in {0}, y in {1}
    equation = Or([Eq("x", "0"), Eq("y", "1")])
    values = {"x": ["0"], "y": ["1"]}
    self.assertEquals(equation, equation.simplify(values))

    # x == 0 && x == 0 with x in {0}
    equation = And([Eq("x", "0"), Eq("x", "0")])
    values = {"x": ["0"]}
    self.assertEquals(Eq("x", "0"), equation.simplify(values))

    # x == y with x in {0, 1} and y in {1, 2}
    equation = Eq("x", "y")
    values = {"x": ["0", "1"], "y": ["1", "2"]}
    self.assertEquals(And([Eq("x", "1"), Eq("y", "1")]),
                      equation.simplify(values))


if __name__ == "__main__":
  unittest.main()
