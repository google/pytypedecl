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

import sys
import textwrap
import unittest
from pytypedecl import pytd
from pytypedecl.parse import parser
from pytypedecl.parse import visitors


class ParserTest(unittest.TestCase):
  """Test utility class. Knows how to parse PYTD and compare source code."""

  def setUp(self):
    self.parser = parser.TypeDeclParser()

  def Parse(self, src, version=None):
    # TODO: Using self.parser here breaks tests. Why?
    tree = parser.TypeDeclParser(version=version).Parse(
        textwrap.dedent(src))
    tree.Visit(visitors.VerifyVisitor())
    return tree

  def ToSource(self, src_or_tree):
    # TODO: The callers are not consistent in how they use this
    #                  and in most (all?) cases they know whether they're
    #                  passing in a source string or parse tree. It would
    #                  be better if all the calles were consistent.
    if isinstance(src_or_tree, basestring):
      # If we trust Parse and Print, we can canonical-ize by:
      #   return pytd.Print(self.Parse(src_or_tree + "\n"))
      # This depends on pytd.Print not changing indents, which shouldn't happen:
      return src_or_tree
    else:  # isinstance(src_or_tree, tuple):
      src_or_tree.Visit(visitors.VerifyVisitor())
      return pytd.Print(src_or_tree)

  def AssertSourceEquals(self, src_or_tree_1, src_or_tree_2):
    # Strip leading "\n"s for convenience
    src1 = self.ToSource(src_or_tree_1).strip() + "\n"
    src2 = self.ToSource(src_or_tree_2).strip() + "\n"
    # Due to differing opinions on the form of debug output, do
    # two checks:
    if src1 != src2:
      sys.stdout.flush()
      sys.stderr.flush()
      print >>sys.stderr, "Source files differ:"
      print >>sys.stderr, "-" * 36, " Actual ", "-" * 36
      print >>sys.stderr, textwrap.dedent(src1).strip()
      print >>sys.stderr, "-" * 36, "Expected", "-" * 36
      print >>sys.stderr, textwrap.dedent(src2).strip()
      print >>sys.stderr, "-" * 80
      self.maxDiff = None  # for better diff output (assertMultiLineEqual)
      self.assertMultiLineEqual(src1, src2)
      self.fail("source files differ")  # Should never reach here

  def ApplyVisitorToString(self, data, visitor):
    tree = self.Parse(data)
    new_tree = tree.Visit(visitor)
    return pytd.Print(new_tree)
