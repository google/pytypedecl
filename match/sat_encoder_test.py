"""Tests for pytypedecl.match.sat_encoder."""

import logging
import sys
import textwrap
import unittest
from pytypedecl import pytd
from pytypedecl import utils
from pytypedecl.match import sat_inferencer
from pytypedecl.parse import builtins as parse_utils


FLAGS = flags.FLAGS  # TODO: move to google/


def _CommonSetup(cls):
  if FLAGS.verbosity:
    logging.basicConfig(level=logging.INFO)

  # TODO: Use full set of builtins. Currently, a limited set is
  #                  used to make it easier to debug the constraints.
  # TODO: sat_inferencer.TypeInferencer()
  cls.inferencer = sat_inferencer.TypeInferencer(
      builtins=parse_utils.ParseBuiltinsFile(
          # The original builtins, but without all the other modules:
          #    "../builtins/__builtin__.pytd"))
          # The stripped-down builtins:
          "../match/builtin_for_testing.pytd"))


class SATEncoderTest(unittest.TestCase):

  # TODO: use setUpClass to call _CommonSetup and
  #                  create a tearDown to clear the stuff that
  #                  TypeInferencer.Solve() modifies

  def setUp(self):
    _CommonSetup(self)

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
        def __add__(self, x:int or float) -> float
      class B:
        def __add__(self, x:bytearray) -> bytearray
      """
    self._ParseSolveCheck(src,
                          {"A": "float",
                           "B": "bytearray"})

  @unittest.skip("Union type 'list or bytearray' not yet implemented")
  def testUnion(self):
    src = """
      class D:
        def append(self, v: int) -> NoneType
      """
    # TODO: The '#' in the class names is from
    #                  sat_encode.ClassType.__str__ and possibly can be removed
    # TODO: why the xrange?
    self._ParseSolveCheck(src,
                          {"D": "list or bytearray",
                           "D#.A": "xrange",
                           "D#.T": "int"})

  def testSingleList(self):
    src = """
      class D:
        def append(self: list, v: float) -> NoneType
      """
    # would require propagating information through mutable parameters which is
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

  @unittest.skip("TODO: failing due to FromPyTD: ClassType<unresolved>(str)")
  # 'UnionType' object has no attribute 'cls'
  def testOr(self):
    src = """
      class C:
        # def join(self, iterable) -> str  # TODO: restore this?
        def join(self, iterable: unicode) -> str or unicode
        def join(self, iterable: iterator) -> str or unicode
      """
    self._ParseSolveCheck(src, {})

  @unittest.skip("TODO: failing due to FromPyTD: ClassType<unresolved>(str)")
  # The problem seems to be because a ClassType.cls doesn't get filled in
  def testAllAtOnce(self):
    src = """
      class A:
        def __add__(self, y: int) -> float
        def __add__(self, y: float) -> float
      class B:
        def __add__(self, y: str) -> bytearray
        def __add__(self, y: bytearray) -> bytearray
      class C:
        def join(self, iterable) -> str
        def join(self, iterable: unicode) -> str or unicode
        def join(self, iterable: iterator) -> str or unicode
      class D:
        def append(self, v: NoneType) -> NoneType
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


# TODO: move to separate test file and create test setup
#                  that includes _CommonSetup()
# TODO: move to pytype/ (see comment in BUILD file)


class Pytype_SATTest(unittest.TestCase):

  # TODO: See comment with SATEncoderTest.setUp
  def setUp(self):
    _CommonSetup(self)

  def testEndToEnd(self):
    # TODO: Maybe set up separate tests in ../examples, accessing
    #                  them via utils.GetDataFile and extracting "expect"
    #                  comments for expected results.
    #              OR: wrap in a simple infrastructure that minimizes the
    #                  amount of boilerplate

    end_to_end_test_src = textwrap.dedent("""
      # Trivial example for testing end-to-end

      def foo(x):
        return x + 1

      def fib(n):
        if n == 0:
          return 1
        else:
          return n * fib(n-1)

      # TODO: uncomment the following
      # class Bar(object):
      #   def __init__(self, an_attr):
      #     self.an_attr = an_attr
      #   def some_method(self, x):
      #     return self.an_attr + x
      # # b = Bar(1.0).some_method(1)
      # # foo(b)
      """)

    end_to_end_test_expect = textwrap.dedent("""
      def fib(n: int) -> int
      def foo(x: int) -> int
      """).strip()

    # TODO: remove the push/pop of logging levels
    save_logging_level = logging.getLogger().getEffectiveLevel()
    logging.getLogger().setLevel(logging.INFO)
    ty = self.inferencer.InferTypesAndSolve(
        end_to_end_test_src,
        debug=True, deep=True, expensive=True)
    logging.getLogger().setLevel(save_logging_level)

    substituted_result = pytd.Print(ty)

    if substituted_result != end_to_end_test_expect:
      print >>sys.stderr, "SAT solver result not expected:"
      print >>sys.stderr, "-" * 36, " Actual ", "-" * 36
      print >>sys.stderr, substituted_result
      print >>sys.stderr, "-" * 36, "Expected", "-" * 36
      print >>sys.stderr, end_to_end_test_expect
      print >>sys.stderr, "-" * 80
      self.maxDiff = None  # for better diff output (assertMultiLineEqual)
      self.assertMultiLineEqual(end_to_end_test_expect, substituted_result)


if __name__ == "__main__":
  unittest.main()
