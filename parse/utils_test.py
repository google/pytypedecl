"""Tests for parse.utils."""

import unittest


from pytypedecl import pytd
from pytypedecl.parse import utils


class UtilsTest(unittest.TestCase):

  def testGetBuiltins(self):
    builtins = utils.GetBuiltins()
    self.assertIsNotNone(builtins)
    self.assertTrue(hasattr(builtins, "modules"))

  def testHasMutableParameters(self):
    builtins = utils.GetBuiltins()
    append = builtins.Lookup("list").Lookup("append")
    self.assertIsInstance(append.signatures[0].params[0], pytd.MutableParameter)

  def testHasCorrectSelf(self):
    builtins = utils.GetBuiltins()
    update = builtins.Lookup("dict").Lookup("update")
    t = update.signatures[0].params[0].type
    self.assertIsInstance(t, pytd.GenericType)
    self.assertEquals(t.base_type, pytd.NamedType("dict"))


if __name__ == "__main__":
  unittest.main()
