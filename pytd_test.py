"""Tests for pytd."""

import unittest
from pytypedecl import pytd


class TestPytd(unittest.TestCase):
  """Test the simple functionality in pytd.py."""

  def setUp(self):
    self.int = pytd.ClassType("int")
    self.none_type = pytd.ClassType("NoneType")
    self.float = pytd.ClassType("float")

  def testUnionTypeEq(self):
    u1 = pytd.UnionType((self.int, self.float))
    u2 = pytd.UnionType((self.float, self.int))
    self.assertEqual(u1, u2)
    self.assertEqual(u2, u1)
    self.assertEqual(u1.type_list, (self.int, self.float))
    self.assertEqual(u2.type_list, (self.float, self.int))

  def testUnionTypeNe(self):
    u1 = pytd.UnionType((self.int, self.float))
    u2 = pytd.UnionType((self.float, self.int, self.none_type))
    self.assertNotEqual(u1, u2)
    self.assertNotEqual(u2, u1)
    self.assertEqual(u1.type_list, (self.int, self.float))
    self.assertEqual(u2.type_list, (self.float, self.int, self.none_type))

if __name__ == "__main__":
  unittest.main()
