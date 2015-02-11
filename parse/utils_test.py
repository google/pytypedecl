"""Tests for parse.utils."""

import unittest


from pytypedecl import pytd
from pytypedecl.parse import utils


class UtilsTest(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    cls.builtins = utils.GetBuiltins()

  def testGetBuiltins(self):
    self.assertIsNotNone(self.builtins)
    self.assertTrue(hasattr(self.builtins, "modules"))

  def testHasMutableParameters(self):
    append = self.builtins.Lookup("list").Lookup("append")
    self.assertIsInstance(append.signatures[0].params[0], pytd.MutableParameter)

  def testHasCorrectSelf(self):
    update = self.builtins.Lookup("dict").Lookup("update")
    t = update.signatures[0].params[0].type
    self.assertIsInstance(t, pytd.GenericType)
    self.assertEquals(t.base_type, pytd.NamedType("dict"))

  def testHasObjectSuperClass(self):
    cls = self.builtins.Lookup("int")
    self.assertEquals(cls.parents, (pytd.NamedType("object"),))
    cls = self.builtins.Lookup("object")
    self.assertEquals(cls.parents, ())


if __name__ == "__main__":
  unittest.main()
