"""Tests for pytypedecl.match.sat_encoder."""

import logging
import unittest


from pytypedecl import optimize
from pytypedecl import pytd
from pytypedecl.match import sat_encoder
from pytypedecl.parse import utils
from pytypedecl.parse import visitors


class SatEncoderTest(unittest.TestCase):

  def setUp(self):
    builtins = utils.GetBuiltins()
    builtins = builtins.Visit(optimize.ExpandSignatures())
    builtins = visitors.LookupClasses(builtins)
    self.builtins = builtins

    int_cls = builtins.Lookup("int")
    self.int_type = pytd.ClassType("int")
    self.int_type.cls = int_cls

    float_cls = builtins.Lookup("float")
    self.float_type = pytd.ClassType("float")
    self.float_type.cls = float_cls

    object_cls = builtins.Lookup("object")
    self.object_type = pytd.ClassType("object")
    self.object_type.cls = object_cls

    none_cls = builtins.Lookup("NoneType")
    self.none_type = pytd.ClassType("NoneType")
    self.none_type.cls = none_cls

  def _Solve(self, incomplete_classes):
    sat = sat_encoder.SatEncoder()
    sat.Generate(self.builtins.classes, incomplete_classes)
    return sat.Solve()

  def testMembersDirectFromClass(self):
    cls_a = pytd.Class("A", (),
                       (self.builtins.Lookup("int").Lookup("__add__"),),
                       (), ())
    cls_b = pytd.Class("B", (),
                       (self.builtins.Lookup("bytearray").Lookup("__add__"),),
                       (), ())
    res = self._Solve([cls_a, cls_b])

    self.assertEqual(res[cls_a], self.builtins.Lookup("int"))
    self.assertEqual(res[cls_b], self.builtins.Lookup("bytearray"))

  def testSingleList(self):
    cls_d = pytd.Class("D", (), (pytd.Function("append", (
        pytd.Signature((pytd.Parameter("self", self.object_type),
                        pytd.Parameter("v", self.int_type)),
                       self.none_type, (), (), False),)),),
                       (), ())
    res = self._Solve([cls_d])

    self.assertEqual(res[cls_d], self.builtins.Lookup("list"))
    self.assertEqual(res[pytd.Class("D#.T", (), (), (), ())],
                     self.builtins.Lookup("int"))

  def testTwoLists(self):
    cls_d = pytd.Class("D", (), (pytd.Function("append", (
        pytd.Signature((pytd.Parameter("self", self.object_type),
                        pytd.Parameter("v", self.int_type)),
                       self.none_type, (), (), False),)),),
                       (), ())
    cls_d2 = pytd.Class("D2", (), (pytd.Function("remove", (
        pytd.Signature((pytd.Parameter("self", self.object_type),
                        pytd.Parameter("v", self.float_type)),
                       self.none_type, (), (), False),)),),
                        (), ())
    res = self._Solve([cls_d, cls_d2])

    self.assertEqual(res[cls_d], self.builtins.Lookup("list"))
    self.assertEqual(res[pytd.Class("D#.T", (), (), (), ())],
                     self.builtins.Lookup("int"))
    self.assertEqual(res[cls_d2], self.builtins.Lookup("list"))
    self.assertEqual(res[pytd.Class("D2#.T", (), (), (), ())],
                     self.builtins.Lookup("float"))

  @unittest.skip("Not yet supported.")
  def testUnion(self):
    cls_a = pytd.Class("A", (), (pytd.Function("__add__", (
        self.builtins.Lookup("int").Lookup("__add__").signatures +
        self.builtins.Lookup("float").Lookup("__add__").signatures)),),
                       (), ())
    res = self._Solve([cls_a])

    self.assertEqual(res[cls_a],
                     pytd.UnionType((self.int_type, self.float_type)))

  def testAllAtOnce(self):
    cls_a = pytd.Class("A", (),
                       (self.builtins.Lookup("int").Lookup("__add__"),),
                       (), ())
    cls_b = pytd.Class("B", (),
                       (self.builtins.Lookup("bytearray").Lookup("__add__"),),
                       (), ())
    cls_c = pytd.Class("C", (), (self.builtins.Lookup("str").Lookup("join"),),
                       (), ())
    cls_d = pytd.Class("D", (), (pytd.Function("append", (
        pytd.Signature((pytd.Parameter("self", self.object_type),
                        pytd.Parameter("v", self.int_type)),
                       self.none_type, (), (), False),)),),
                       (), ())
    cls_d2 = pytd.Class("D2", (), (pytd.Function("remove", (
        pytd.Signature((pytd.Parameter("self", self.object_type),
                        pytd.Parameter("v", self.float_type)),
                       self.none_type, (), (), False),)),),
                        (), ())

    res = self._Solve([cls_a, cls_b, cls_c, cls_d, cls_d2])

    self.assertEqual(res[cls_a], self.builtins.Lookup("int"))
    self.assertEqual(res[cls_b], self.builtins.Lookup("bytearray"))
    self.assertEqual(res[cls_c], self.builtins.Lookup("str"))
    self.assertEqual(res[cls_d], self.builtins.Lookup("list"))
    self.assertEqual(res[pytd.Class("D#.T", (), (), (), ())],
                     self.builtins.Lookup("int"))
    self.assertEqual(res[cls_d2], self.builtins.Lookup("list"))
    self.assertEqual(res[pytd.Class("D2#.T", (), (), (), ())],
                     self.builtins.Lookup("float"))


if __name__ == "__main__":
  # logging.basicConfig(level=logging.INFO)
  unittest.main()
