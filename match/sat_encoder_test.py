"""Tests for pytypedecl.match.sat_encoder."""

import logging
import textwrap
import unittest
from pytypedecl import pytd
from pytypedecl.match import sat_inferencer
from pytypedecl.parse import utils as parse_utils


FLAGS = flags.FLAGS  # TODO: move to google/


class SATEncoderTest(unittest.TestCase):

  def setUp(self):
    if FLAGS.verbosity:
      logging.basicConfig(level=logging.INFO)

    # TODO: sat_inferencer.TypeInferencer()
    self.inferencer = sat_inferencer.TypeInferencer(
        builtins=parse_utils.GetBuiltinsFile(
            # The original builtins, but without all the other modules:
            #    "builtins/__builtin__.pytd"))
            # The stripped-down builtins:
            "match/builtin_for_testing.pytd"))

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

    xrange_cls = self.inferencer.builtins.Lookup("xrange")
    self.xrange_type = pytd.ClassType("xrange")
    self.xrange_type.cls = xrange_cls

    object_cls = self.inferencer.builtins.Lookup("object")
    self.object_type = pytd.ClassType("object")
    self.object_type.cls = object_cls

    none_cls = self.inferencer.builtins.Lookup("NoneType")
    self.none_type = pytd.ClassType("NoneType")
    self.none_type.cls = none_cls

  def _ParseSolveCheck(self, src, expected):
    res = self.inferencer.ParseAndSolve(textwrap.dedent(src))
    self.assertEqual(expected, res)

  def testMembersDirectFromParsedClass1(self):
    # Note that this test is a bit of a cheat: def _add__(self:float, ...)
    src = """
      class A:
        def __add__(self: float, y: int) -> float
        def __add__(self: float, y: float) -> float
      class B:
        def __add__(self: bytearray, y: str) -> bytearray
        def __add__(self: bytearray, y: bytearray) -> bytearray
      """
    self._ParseSolveCheck(src,
                          {"A": self.float_type,
                           "B": self.bytearray_type})

  def testMembersDirectFromParsedClass2(self):
    # The same as testMembersDirectFromClass1 with the cheat removed.
    src = """
      class A:
        def __add__(self: A, x:int or float) -> float
      class B:
        def __add__(self: B, x:bytearray) -> bytearray
      """
    self._ParseSolveCheck(src,
                          {"A": self.float_type,
                           "B": self.bytearray_type})

  @unittest.skip("Not yet implemented")
  def testUnion(self):
    src = """
      class D:
        def append(self, v: int) -> NoneType
      """
    # TODO: The '#' in the class names is from
    #                  sat_encode.ClassType.__str__ and possibly can be removed
    self._ParseSolveCheck(src,
                          {"D": pytd.UnionType(
                              (self.list_type, self.bytearray_type)),
                           "D#.T": self.int_type})

  def testSingleList(self):
    src = """
      class D:
        def append(self: list, v: float) -> NoneType
      """
    # would require propogating information through mutable parameters which is
    # not yet supported in this system.
    self._ParseSolveCheck(src,
                          {"D": self.list_type,
                           "D#.T": self.float_type,
                           "list": self.list_type})

  def testSingleListInOut(self):
    src = """
      class D:
        def append(self: list, v: A) -> NoneType
        def __getitem__(self: list, i) -> A

      class A:
        def __add__(self: float, y: int) -> float
        def __add__(self: float, y: float) -> float
      """
    self._ParseSolveCheck(src,
                          {"A": self.float_type,
                           "D": self.list_type,
                           "D#.K": self.list_type,
                           "D#.T": self.float_type,
                           "D#.V": self.xrange_type,
                           "list": self.list_type})

  def testTwoLists(self):
    src = """
      class D:
        def append(self: list, v: NoneType) -> NoneType
      class D2:
        def remove(self: list, v: float) -> NoneType
      """
    # TODO: D#.A is actually wrong. - should be D#.T
    #                  See testSingleList
    #  ... according to kramm, the bug should go away if, in
    #  builtins_for_testing.pytd, define append as
    #     def append(self, object: T) -> NoneType
    self._ParseSolveCheck(src,
                          {"D": self.list_type,
                           "D#.T": self.none_type,
                           "D2": self.list_type,
                           "D2#.T": self.float_type,
                           "list": self.list_type})

  def testUseOneOfManySignatures(self):
    src = """
      class A:
        def __add__(self, v: int) -> float
      """
    self._ParseSolveCheck(src,
                          {"A": self.float_type})

  @unittest.skip("TODO: Failing probably due to a set ordering issue.")
  def testAllAtOnce(self):
    src = """
      class A:
        def __add__(self: float, y: int) -> float
        def __add__(self: float, y: float) -> float
      class B:
        def __add__(self: bytearray, y: str) -> bytearray
        def __add__(self: bytearray, y: bytearray) -> bytearray
      class C:
        def join(self: str, iterable) -> str
        def join(self: str, iterable: unicode) -> str or unicode
        def join(self: str, iterable: iterator) -> str or unicode
      class D:
        def append(self: list, v: NoneType) -> NoneType
      """
    # TODO: D#.A is actually wrong - should be D#.T.
    #              See testSingleList
    self._ParseSolveCheck(src,
                          {"B": self.bytearray_type,
                           "C": self.str_type,
                           "D": self.list_type,
                           "D#.A": self.none_type,
                           "D2": self.list_type,
                           "D2#.T": self.float_type})


if __name__ == "__main__":
  unittest.main()
