"""Tests for slots.py."""

import unittest
from pytypedecl import slots


class TestPytd(unittest.TestCase):
  """Test the operator mappings in slots.py."""

  def testBinaryOperatorMapping(self):
    slots.GetBinaryOperatorMapping().get("ADD")  # smoke test


if __name__ == "__main__":
  unittest.main()
