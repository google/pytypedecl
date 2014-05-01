# -*- coding:utf-8; python-indent:2; indent-tabs-mode:nil -*-
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility classes for testing the PYTD parser."""

import re
import textwrap
import unittest
from pytypedecl import pytd
from pytypedecl.parse import parser
from pytypedecl.parse import visitors


class ParserTest(unittest.TestCase):
  """Test utility class. Knows how to parse PYTD and compare source code."""

  def setUp(self):
    self.parser = parser.PyParser()

  def ToSource(self, src_or_tree):
    if isinstance(src_or_tree, tuple):
      return src_or_tree.Visit(visitors.PrintVisitor())
    else:
      return src_or_tree

  def AssertSourceEquals(self, src_or_tree_1, src_or_tree_2):
    # As long as the parser is not aware of indent, we can just shrink
    # any whitespace to a single space without changing the interpretation.
    src1 = self.ToSource(src_or_tree_1)
    src2 = self.ToSource(src_or_tree_2)

    simplified1 = re.sub(r"\s+", " ", src1.strip())
    simplified2 = re.sub(r"\s+", " ", src2.strip())

    if simplified1 != simplified2:
      print "Source files differ:"
      print "-"*80
      print textwrap.dedent(src1).strip()
      print "-"*80
      print textwrap.dedent(src2).strip()
      print "-"*80
      self.fail("source files differ")

  def ApplyVisitorToString(self, data, visitor):
    tree = self.parser.Parse(data)
    new_tree = tree.Visit(visitor)
    return pytd.Print(new_tree)

