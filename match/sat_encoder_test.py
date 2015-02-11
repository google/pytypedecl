"""Tests for pytypedecl.match.sat_encoder."""

import logging
import textwrap
import unittest
from pytypedecl import pytd
from pytypedecl.match import sat_inferencer
from pytypedecl.parse import utils as parse_utils


FLAGS = flags.FLAGS  # TODO: move to google/


class SATEncoderTest(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    if FLAGS.verbosity:
      logging.basicConfig(level=logging.INFO)

    # TODO: sat_inferencer.TypeInferencer()
    cls.inferencer = sat_inferencer.TypeInferencer(
        builtins=parse_utils.GetBuiltinsFile(
            # The original builtins, but without all the other modules:
            #    "builtins/__builtin__.pytd"))
            # The stripped-down builtins:
            "match/builtin_for_testing.pytd"))

  def _ParseSolveCheck(self, src, expected):
    res = self.inferencer.ParseAndSolve(textwrap.dedent(src))
    # TODO: If we can't guarantee that two different classes have the
    #                  same print form (e.g., None vs NoneType), parse the
    #                  expected and do == match against the ASTs.
    res_to_name = {k: pytd.Print(v) for k, v in res.items()}
    self.assertEqual(expected, res_to_name)

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
                          {"A": "float",
                           "B": "bytearray"})

  def testMembersDirectFromParsedClass2(self):
    # The same as testMembersDirectFromClass1 with the cheat removed.
    src = """
      class A:
        def __add__(self: A, x:int or float) -> float
      class B:
        def __add__(self: B, x:bytearray) -> bytearray
      """
    self._ParseSolveCheck(src,
                          {"A": "float",
                           "B": "bytearray"})

  @unittest.skip("Not yet implemented")
  def testUnion(self):
    src = """
      class D:
        def append(self, v: int) -> NoneType
      """
    # TODO: The '#' in the class names is from
    #                  sat_encode.ClassType.__str__ and possibly can be removed
    self._ParseSolveCheck(src,
                          {"D": "list or bytearray",
                           "D#.A": "xrange",
                           "D#.T": "int"})

  def testSingleList(self):
    src = """
      class D:
        def append(self: list, v: float) -> NoneType
      """
    # would require propogating information through mutable parameters which is
    # not yet supported in this system.
    self._ParseSolveCheck(src,
                          {"D": "list",
                           "D#.T": "float",
                           "list": "list"})

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
                          {"A": "float",
                           "D": "list",
                           "D#.K": "list",
                           "D#.T": "float",
                           "D#.V": "xrange",
                           "list": "list"})

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
                          {"D": "list",
                           "D#.T": "NoneType",
                           "D2": "list",
                           "D2#.T": "float",
                           "list": "list"})

  def testUseOneOfManySignatures(self):
    src = """
      class A:
        def __add__(self, v: int) -> float
      """
    self._ParseSolveCheck(src,
                          {"A": "float"})

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
                          {"B": "bytearray",
                           "C": "str",
                           "D": "list",
                           "D#.A": "NoneType",
                           "D2": "list",
                           "D2#.T": "float"})


if __name__ == "__main__":
  unittest.main()
