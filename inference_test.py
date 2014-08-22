"""Base class for testing pytd inference engines."""

import sys
import textwrap
import unittest


from pytypedecl import parse
from pytypedecl import pytd
from pytypedecl import utils
from pytypedecl.parse import visitors

import parse.utils


class PyTDTestCase(unittest.TestCase):
  """Base class for implementing tests that check PyTD output.
  """

  def setUp(self):
    self.bool = pytd.ClassType("bool")
    self.dict = pytd.ClassType("dict")
    self.float = pytd.ClassType("float")
    self.int = pytd.ClassType("int")
    self.list = pytd.ClassType("list")
    self.none_type = pytd.ClassType("NoneType")
    self.object = pytd.ClassType("object")
    self.str = pytd.ClassType("str")
    self.tuple = pytd.ClassType("tuple")

    self.intorfloat = pytd.UnionType((self.float, self.int))
    self.intorstr = pytd.UnionType((self.int, self.str))

    # Make get_pytd load _builtin_pytds
    self.builtin_pytds = parse.utils.GetBuiltins()
    for ty in (self.int, self.none_type, self.float,
               self.intorfloat, self.tuple, self.str,
               self.object, self.list, self.dict, self.bool):
      visitors.FillInClasses(ty, self.builtin_pytds)

  @staticmethod
  def HasSignature(func, parameter_types, return_type):
    parameter_types = tuple(parameter_types)
    found = False
    for sig in func.signatures:
      if (parameter_types == tuple(p.type for p in sig.params) and
          return_type == sig.return_type):
        found = True
        break
    return found

  def assertHasOnlySignatures(self, func, *sigs):
    for parameter_types, return_type in sigs:
      if not self.HasSignature(func, parameter_types, return_type):
        self.fail("Could not find signature: {} -> {} in {}".
                  format(parameter_types, return_type, func))
    self.assertEqual(len(func.signatures), len(sigs),
                     "{} has the wrong number of signatures ({}), expected {}".
                     format(func, len(func.signatures), len(sigs)))

  def assertHasSignature(self, func, parameter_types, return_type):
    if not self.HasSignature(func, parameter_types, return_type):
      self.fail("Could not find signature: {} -> {} in {}".
                format(parameter_types, return_type, func))

  def assertNotHasSignature(self, func, parameter_types, return_type):
    if self.HasSignature(func, parameter_types, return_type):
      self.fail("Found signature: {} -> {} in {}".
                format(parameter_types, return_type, func))


class InferenceTestCase(PyTDTestCase):
  """A set of tests that can be applied to any inference system.
  """

  def Infer(self, srccode):
    """Infer types for the source code treating it as a module.

    Args:
      srccode: The source code of a module. Treat it as "__main__".

    Returns:
      A pytd.TypeDeclUnit
    """
    raise NotImplementedError

  def InferDedent(self, srccode):
    """Prints useful output and dedents the code before calling infer."""
    srccode = textwrap.dedent(srccode)
    print "========== source =========="
    print srccode
    print "=="
    sys.stdout.flush()
    types = self.Infer(srccode)
    sys.stdout.flush()
    print "=========== PyTD ==========="
    print pytd.Print(types)
    print "=="
    return types


class FunctionTypeTests(InferenceTestCase):

  def testFlowAndReplacementSanity(self):
    ty = self.InferDedent("""
      def f(x):
        if x:
          x = 42
          y = x
          x = 1
        return x + 4
      f(4)
    """)
    self.assertHasOnlySignatures(ty.Lookup("f"),
                                 ((self.int,), self.int))

  def testMultipleReturns(self):
    ty = self.InferDedent("""
      def f(x):
        if x:
          return 1
        else:
          return 1.5
      f(1)
    """)
    self.assertHasOnlySignatures(ty.Lookup("f"),
                                 ((self.int,), self.intorfloat))

  def testLoopsSanity(self):
    ty = self.InferDedent("""
      def f():
        x = 4
        y = -10
        for i in xrange(1000):
          x = x + (i+y)
          y = i
        return x
      f()
    """)
    self.assertHasOnlySignatures(ty.Lookup("f"),
                                 ((), self.int))

  def testAddInt(self):
    ty = self.InferDedent("""
      def f(x):
        return x + 1
      f(3.2)
      f(3)
    """)
    self.assertHasSignature(ty.Lookup("f"), (self.int,), self.int)
    self.assertHasSignature(ty.Lookup("f"), (self.float,), self.float)

  def testAddFloat(self):
    ty = self.InferDedent("""
      def f(x):
        return x + 1.2
      f(3.2)
      f(3)
    """)
    self.assertHasSignature(ty.Lookup("f"), (self.intorfloat,), self.float)

  def testAddStr(self):
    ty = self.InferDedent("""
      def f(x):
        return x + "Test"
      f(3.2)
    """)
    self.assertItemsEqual(ty.functions, [])

  def testClassSanity(self):
    ty = self.InferDedent("""
      class A(object):
        def __init__(self):
          self.x = 1

        def get_x(self):
          return self.x

        def set_x(self, x):
          self.x = x
      a = A()
      y = a.x
      x1 = a.get_x()
      a.set_x(1.2)
      x2 = a.get_x()
    """)
    self.assertHasSignature(ty.Lookup("A").Lookup("set_x"),
                            (pytd.ClassType("A"), self.float,), self.none_type)
    self.assertHasSignature(ty.Lookup("A").Lookup("get_x"),
                            (pytd.ClassType("A"),), self.intorfloat)

  @unittest.skip("This will not work until proper stack handling during out "
                 "of order traversal is implemented. And __lt__ and __gt__.")
  def testBooleanOp(self):
    ty = self.InferDedent("""
      def f(x, y):
        return 1 < x < 10
        return 1 > x > 10
      f(1, 2)
    """)
    self.assertHasSignature(ty.Lookup("f"), (self.int, self.int), self.bool)


class ParametricTypeTests(InferenceTestCase):

  def testTuplePassThrough(self):
    ty = self.InferDedent("""
      def f(x):
        return x
      f((3, "str"))
    """)
    self.assertHasOnlySignatures(ty.Lookup("f"),
                                 ((pytd.GenericType(self.tuple,
                                                    (self.intorstr,)),),
                                  pytd.GenericType(self.tuple,
                                                   (self.intorstr,))))

  def testTuple(self):
    ty = self.InferDedent("""
      def f(x):
        return x[0]
      f((3, "str"))
    """)
    self.assertHasOnlySignatures(ty.Lookup("f"),
                                 ((pytd.GenericType(self.tuple,
                                                    (self.intorstr,)),),
                                  self.intorstr))

  def testTupleSwap(self):
    ty = self.InferDedent("""
      def f(x):
        return (x[1], x[0])
      f((3, "str"))
    """)
    self.assertHasOnlySignatures(ty.Lookup("f"),
                                 ((pytd.GenericType(self.tuple,
                                                    (self.intorstr,)),),
                                  pytd.GenericType(self.tuple,
                                                   (self.intorstr,))))

  def testEmptyTuple(self):
    ty = self.InferDedent("""
      def f():
        return ()
      f()
    """)
    self.assertHasOnlySignatures(ty.Lookup("f"),
                                 ((),
                                  pytd.GenericType(self.tuple,
                                                   (self.object,))))

  def testSetsSanity(self):
    ty = self.InferDedent("""
      def f():
        x = set([1])
        x.add(10)
        return x
      f()
    """)
    self.assertHasOnlySignatures(ty.Lookup("f"),
                                 ((), pytd.GenericType(pytd.ClassType("set"),
                                                       (self.int,))))

  def testSetsAdd(self):
    ty = self.InferDedent("""
      def f():
        x = set([])
        x.add(1)
        x.add(10)
        return x
      f()
    """)
    self.assertHasOnlySignatures(ty.Lookup("f"),
                                 ((), pytd.GenericType(pytd.ClassType("set"),
                                                       (self.int,))))

  def testSets(self):
    ty = self.InferDedent("""
      def f():
        x = set([1,2,3])
        if x:
          x = x | set()
          y = x
          return x
        else:
          x.add(10)
          return x
      f()
    """)
    self.assertHasOnlySignatures(ty.Lookup("f"),
                                 ((), pytd.GenericType(pytd.ClassType("set"),
                                                       (self.int,))))

  def testListLiteral(self):
    ty = self.InferDedent("""
      def f():
        return [1, 2, 3]
      f()
    """)
    self.assertHasOnlySignatures(ty.Lookup("f"),
                                 ((),
                                  pytd.GenericType(self.list,
                                                   (self.int,))))

  def testListAppend(self):
    ty = self.InferDedent("""
      def f():
        x = []
        x.append(1)
        x.append(2)
        x.append(3)
        return x
      f()
    """)
    self.assertHasOnlySignatures(ty.Lookup("f"),
                                 ((),
                                  pytd.GenericType(self.list,
                                                   (self.int,))))

  def testListConcat(self):
    ty = self.InferDedent("""
      def f():
        x = []
        x.append(1)
        x.append(2)
        x.append(3)
        return [0] + x
      f()
    """)
    self.assertHasOnlySignatures(ty.Lookup("f"),
                                 ((),
                                  pytd.GenericType(self.list,
                                                   (self.int,))))

  def testListConcatMultiType(self):
    ty = self.InferDedent("""
      def f():
        x = []
        x.append(1)
        x.append("str")
        return x + [1.3] + x
      f()
    """)
    self.assertHasOnlySignatures(
        ty.Lookup("f"),
        ((),
         pytd.GenericType(self.list,
                          (pytd.UnionType((self.int, self.float, self.str)),))))

  def testListConcatUnlike(self):
    ty = self.InferDedent("""
      def f():
        x = []
        x.append(1)
        x.append(2)
        x.append(3)
        return ["str"] + x
      f()
    """)
    self.assertHasOnlySignatures(ty.Lookup("f"),
                                 ((),
                                  pytd.GenericType(self.list,
                                                   (self.intorstr,))))

  def testDictLiteral(self):
    ty = self.InferDedent("""
      def f():
        return {"test": 1, "arg": 42}
      f()
    """)
    self.assertHasOnlySignatures(ty.Lookup("f"),
                                 ((),
                                  pytd.GenericType(self.dict,
                                                   (self.str, self.int))))

  def testDictUpdate(self):
    ty = self.InferDedent("""
      def f():
        d = {}
        d["test"] = 1
        d["arg"] = 42
        return d
      f()
    """)
    self.assertHasOnlySignatures(ty.Lookup("f"),
                                 ((),
                                  pytd.GenericType(self.dict,
                                                   (self.str, self.int))))


class PyTreeTests(InferenceTestCase):

  def setUp(self):
    with open(utils.GetDataFile("examples/pytree.py"), "r") as infile:
      self.ty = self.Infer(infile.read())

  def testTypeRepr(self):
    self.assertHasOnlySignatures(self.ty.Lookup("type_repr"),
                                 ((self.object), self.str))

  def testClassesExist(self):
    self.assertIn("Base", self.ty.classes)
    self.assertIn("Node", self.ty.classes)
    self.assertIn("Leaf", self.ty.classes)

  # TODO(ampere): Add many more tests


class StringIOTests(InferenceTestCase):

  def setUp(self):
    with open(utils.GetDataFile("examples/StringIO.py"), "r") as infile:
      self.ty = self.Infer(infile.read())
    try:
      self.stringio_cls = self.ty.Lookup("StringIO")
    except KeyError:
      self.stringio_cls = None
      # Continue to the test it will fail if it needs the cls
    self.stringio_type = pytd.ClassType("StringIO")
    self.stringio_type.cls = self.stringio_cls

  def testComplainIfclosed(self):
    self.assertHasOnlySignatures(self.ty.Lookup("_complain_ifclosed"),
                                 ((self.bool), self.none_type))

  def testClassesExist(self):
    self.assertIn("StringIO", self.ty.classes)

  def testStringIOIter(self):
    self.assertHasOnlySignatures(self.stringio_cls.Lookup("__iter__"),
                                 ((self.stringio_type), self.stringio_type))

  def testStringIOGetValue(self):
    self.assertHasOnlySignatures(self.stringio_cls.Lookup("get_value"),
                                 ((self.stringio_type), self.str))

  # TODO(ampere): Add many more tests
