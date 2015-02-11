"""Tests for pytypedecl.match.sat_encoder."""

import logging
import unittest


from pytypedecl import optimize
from pytypedecl import pytd
from pytypedecl.match import sat_encoder
from pytypedecl.parse import utils
from pytypedecl.parse import visitors


@unittest.skip("Too slow.")
class SatEncoderTest(unittest.TestCase):

  def setUp(self):
    builtins = utils.GetBuiltins()
    builtins = builtins.Visit(optimize.ExpandSignatures())
    builtins = visitors.LookupClasses(builtins)
    self.builtins = builtins

    list_cls = builtins.Lookup("list")
    self.list_type = pytd.ClassType("list")
    self.list_type.cls = list_cls

    bytearray_cls = builtins.Lookup("bytearray")
    self.bytearray_type = pytd.ClassType("bytearray")
    self.bytearray_type.cls = bytearray_cls

    str_cls = builtins.Lookup("str")
    self.str_type = pytd.ClassType("str")
    self.str_type.cls = str_cls

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
    res = sat.Solve()
    return res

  def testMembersDirectFromClass(self):
    cls_a = pytd.Class("A", (),
                       (self.builtins.Lookup("float").Lookup("__add__"),),
                       (), ())
    cls_b = pytd.Class("B", (),
                       (self.builtins.Lookup("bytearray").Lookup("__add__"),),
                       (), ())
    res = self._Solve([cls_a, cls_b])

    self.assertEqual(res[cls_a], self.float_type)
    self.assertEqual(res[cls_b], self.bytearray_type)

  @unittest.skip("Not yet implemented")
  def testUnion(self):
    cls_d = pytd.Class("D", (), (pytd.Function("append", (
        pytd.Signature((pytd.Parameter("self", self.object_type),
                        pytd.Parameter("v", self.int_type)),
                       self.none_type, (), (), False),)),),
                       (), ())
    res = self._Solve([cls_d])

    self.assertEqual(res[cls_d],
                     pytd.UnionType((self.list_type, self.bytearray_type)))
    self.assertEqual(res[pytd.Class("D#.T", (), (), (), ())],
                     self.int_type)

  def testSingleList(self):
    cls_d = pytd.Class("D", (), (pytd.Function("append", (
        pytd.Signature((pytd.Parameter("self", self.list_type),
                        pytd.Parameter("v", self.float_type)),
                       self.none_type, (), (), False),)),),
                       (), ())
    res = self._Solve([cls_d])

    self.assertEqual(res[cls_d], self.list_type)
    # TODO: D#.A is actually wrong. It should be D#.T. However that
    # would require propogating information through mutable parameters which is
    # not yet supported in this system.
    self.assertEqual(res[pytd.Class("D#.A", (), (), (), ())],
                     self.float_type)

  def testSingleListInOut(self):
    cls_a = pytd.Class("A", (),
                       (self.builtins.Lookup("float").Lookup("__add__"),),
                       (), ())
    type_a = pytd.ClassType("A")
    type_a.cls = cls_a

    cls_d = pytd.Class("D", (), (
        pytd.Function("append", (
            pytd.Signature((pytd.Parameter("self", self.list_type),
                            pytd.Parameter("v", type_a)),
                           self.none_type, (), (), False),)),
        pytd.Function("__getitem__", (
            pytd.Signature((pytd.Parameter("self", self.list_type),
                            pytd.Parameter("i", self.object_type)),
                           type_a, (), (), False),))),
                       (), ())
    res = self._Solve([cls_d, cls_a])

    self.assertEqual(res[cls_d], self.list_type)
    self.assertEqual(res[pytd.Class("D#.T", (), (), (), ())],
                     self.float_type)

  def testTwoLists(self):
    cls_d = pytd.Class("D", (), (pytd.Function("append", (
        pytd.Signature((pytd.Parameter("self", self.list_type),
                        pytd.Parameter("v", self.none_type)),
                       self.none_type, (), (), False),)),),
                       (), ())
    cls_d2 = pytd.Class("D2", (), (pytd.Function("remove", (
        pytd.Signature((pytd.Parameter("self", self.list_type),
                        pytd.Parameter("v", self.float_type)),
                       self.none_type, (), (), False),)),),
                        (), ())
    res = self._Solve([cls_d, cls_d2])

    self.assertEqual(res[cls_d], self.list_type)
    # TODO: D#.A is actually wrong. It should be D#.T. See testSingleList
    self.assertEqual(res[pytd.Class("D#.A", (), (), (), ())],
                     self.none_type)
    self.assertEqual(res[cls_d2], self.list_type)
    self.assertEqual(res[pytd.Class("D2#.T", (), (), (), ())],
                     self.float_type)

  def testUseOneOfManySignatures(self):
    cls_a = pytd.Class("A", (), (pytd.Function("__add__", (
        pytd.Signature((pytd.Parameter("self", self.object_type),
                        pytd.Parameter("v", self.int_type)),
                       self.float_type, (), (), False),)),),
                       (), ())
    res = self._Solve([cls_a])

    self.assertEqual(res[cls_a],
                     self.float_type)

  @unittest.skip("TODO: Failing probably due to a set ordering issue.")
  def testAllAtOnce(self):
    cls_a = pytd.Class("A", (),
                       (self.builtins.Lookup("float").Lookup("__add__"),),
                       (), ())
    cls_b = pytd.Class("B", (),
                       (self.builtins.Lookup("bytearray").Lookup("__add__"),),
                       (), ())
    cls_c = pytd.Class("C", (), (self.builtins.Lookup("str").Lookup("join"),),
                       (), ())
    cls_d = pytd.Class("D", (), (pytd.Function("append", (
        pytd.Signature((pytd.Parameter("self", self.list_type),
                        pytd.Parameter("v", self.none_type)),
                       self.none_type, (), (), False),)),),
                       (), ())
    cls_d2 = pytd.Class("D2", (), (pytd.Function("remove", (
        pytd.Signature((pytd.Parameter("self", self.list_type),
                        pytd.Parameter("v", self.float_type)),
                       self.none_type, (), (), False),)),),
                        (), ())

    res = self._Solve([cls_a, cls_b, cls_c, cls_d, cls_d2])

    self.assertEqual(res[cls_a], self.float_type)
    self.assertEqual(res[cls_b], self.bytearray_type)
    self.assertEqual(res[cls_c], self.str_type)
    self.assertEqual(res[cls_d], self.list_type)
    # TODO: D#.A is actually wrong. It should be D#.T. See testSingleList
    self.assertEqual(res[pytd.Class("D#.A", (), (), (), ())],
                     self.none_type)
    self.assertEqual(res[cls_d2], self.list_type)
    self.assertEqual(res[pytd.Class("D2#.T", (), (), (), ())],
                     self.float_type)


if __name__ == "__main__":
  # logging.basicConfig(level=logging.DEBUG)
  unittest.main()
