"""Tests for pytypedecl.match.sat_encoder."""

import logging
import textwrap
import unittest
from pytypedecl import pytd
from pytypedecl.match import sat_inferencer


FLAGS = flags.FLAGS  # TODO: move to google/


class SATEncoderTest(unittest.TestCase):

  def setUp(self):
    if FLAGS.verbosity:
      logging.basicConfig(level=logging.INFO)

    # TODO: reduce the builtins, to allow shorter, more readable,
    #                  tests (for now - in future, restore builtins)
    self.inferencer = sat_inferencer.TypeInferencer()

    list_cls = self.inferencer.builtins.Lookup("list")
    self.list_type = pytd.ClassType("list")
    self.list_type.cls = list_cls

    bytearray_cls = self.inferencer.builtins.Lookup("bytearray")
    self.bytearray_type = pytd.ClassType("bytearray")
    self.bytearray_type.cls = bytearray_cls

    str_cls = self.inferencer.builtins.Lookup("str")
    self.str_type = pytd.ClassType("str")
    self.str_type.cls = str_cls

    int_cls = self.inferencer.builtins.Lookup("int")
    self.int_type = pytd.ClassType("int")
    self.int_type.cls = int_cls

    float_cls = self.inferencer.builtins.Lookup("float")
    self.float_type = pytd.ClassType("float")
    self.float_type.cls = float_cls

    object_cls = self.inferencer.builtins.Lookup("object")
    self.object_type = pytd.ClassType("object")
    self.object_type.cls = object_cls

    none_cls = self.inferencer.builtins.Lookup("NoneType")
    self.none_type = pytd.ClassType("NoneType")
    self.none_type.cls = none_cls

  def _SolveClasses(self, incomplete_classes):
    parsed_incomplete = pytd.TypeDeclUnit(
        constants=(),
        classes=incomplete_classes,
        functions=(),
        modules={})
    # The following 2 lines are the same as TypeInferencer.ParseAndSolve(),
    # except the parsing has already been done to an AST (but no other
    # processing has been done to the AST):
    incomplete = self.inferencer.LookupParsed(parsed_incomplete)
    return self.inferencer.SolveFromParsedLookedUpClasses(incomplete.classes)

  def testMembersDirectFromClass(self):
    # Note that this test is a bit of a cheat: def _add__(self:float, ...)
    cls_a = pytd.Class(
        "A", (),
        (self.inferencer.builtins.Lookup("float").Lookup("__add__"),),
        (), ())
    cls_b = pytd.Class(
        "B", (),
        (self.inferencer.builtins.Lookup("bytearray").Lookup("__add__"),),
        (), ())
    res = self._SolveClasses([cls_a, cls_b])
    self.assertItemsEqual({cls_a: self.float_type,
                           cls_b: self.bytearray_type},
                          res)

  def testMembersDirectFromParsedClass(self):
    # This is essentially the same as testMembersDirectFromClass with the cheat
    # removed, and using the pytd parser.
    src = """
      class A:
        def __add__(self: A, x:int or float) -> float
      class B:
        def __add__(self: B, x:bytearray) -> bytearray
    """
    src = textwrap.dedent(src)
    # The following 2 lines are the same as TypeInferencer.ParseAndSolve()
    # but keep the parsed result for validation
    parsed_looked_up = self.inferencer.ParseAndLookup(src)
    res = self.inferencer.SolveFromParsedLookedUpClasses(
        parsed_looked_up.classes)
    # Make sure that the classes that were given to the solver were as expected:
    self.assertEqual([c.name for c in parsed_looked_up.classes], ["A", "B"])
    self.assertItemsEqual(
        {parsed_looked_up.classes[0]: self.float_type,
         parsed_looked_up.classes[1]: self.bytearray_type},
        res)

  @unittest.skip("Not yet implemented")
  def testUnion(self):
    cls_d = pytd.Class("D", (), (pytd.Function("append", (
        pytd.Signature((pytd.Parameter("self", self.object_type),
                        pytd.Parameter("v", self.int_type)),
                       self.none_type, (), (), False),)),),
                       (), ())
    res = self._SolveClasses([cls_d])

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
    res = self._SolveClasses([cls_d])

    self.assertEqual(res[cls_d], self.list_type)
    # TODO: D#.A is actually wrong. It should be D#.T. However that
    # would require propogating information through mutable parameters which is
    # not yet supported in this system.
    self.assertEqual(res[pytd.Class("D#.A", (), (), (), ())],
                     self.float_type)

  def testSingleListInOut(self):
    cls_a = pytd.Class(
        "A", (),
        (self.inferencer.builtins.Lookup("float").Lookup("__add__"),),
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
    res = self._SolveClasses([cls_d, cls_a])

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
    res = self._SolveClasses([cls_d, cls_d2])

    self.assertEqual(res[cls_d], self.list_type)
    # TODO: D#.A is actually wrong. It should be D#.T. See testSingleList
    self.assertEqual(res[pytd.Class("D#.A", (), (), (), ())],
                     self.none_type)
    self.assertEqual(res[cls_d2], self.list_type)
    self.assertEqual(res[pytd.Class("D2#.T", (), (), (), ())],
                     self.float_type)

  def testUseOneOfManySignatures(self):
    cls_a_type = pytd.ClassType("A")
    cls_a = pytd.Class("A", (), (pytd.Function("__add__", (
        pytd.Signature((pytd.Parameter("self", cls_a_type),
                        pytd.Parameter("v", self.int_type)),
                       self.float_type, (), (), False),)),),
                       (), ())
    cls_a_type.cls = cls_a
    res = self._SolveClasses([cls_a])

    self.assertEqual(res[cls_a],
                     self.float_type)

  @unittest.skip("TODO: Failing probably due to a set ordering issue.")
  def testAllAtOnce(self):
    cls_a = pytd.Class(
        "A", (),
        (self.inferencer.builtins.Lookup("float").Lookup("__add__"),),
        (), ())
    cls_b = pytd.Class(
        "B", (),
        (self.inferencer.builtins.Lookup("bytearray").Lookup("__add__"),),
        (), ())
    cls_c = pytd.Class(
        "C", (),
        (self.inferencer.builtins.Lookup("str").Lookup("join"),), (), ())
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

    res = self._SolveClasses([cls_a, cls_b, cls_c, cls_d, cls_d2])

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
  unittest.main()
