"""Tests for parse.utils."""

import unittest


class UtilsTest(unittest.TestCase):

  def testGetBuiltins(self):
    builtins = utils.GetBuiltins()
    self.assertIsNotNone(builtins)
    self.assertTrue(hasattr(builtins, "modules"))


if __name__ == '__main__':
  unittest.main()
