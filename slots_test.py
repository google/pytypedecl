"""Tests for slots.py."""

import unittest
from pytypedecl import slots


class TestPytd(unittest.TestCase):
  """Test the operator mappings in slots.py."""

  def testBinaryOperatorMapping(self):
    slots.GetBinaryOperatorMapping().get("ADD")  # smoke test

  def testCompareFunctionMapping(self):
    indexes = slots.GetCompareFunctionMapping().keys()
    # Assert that we have the six basic comparison ops (<, <=, ==, !=, >, >=).
    for i in range(6):
      self.assertIn(i, indexes)


if __name__ == "__main__":
  unittest.main()
