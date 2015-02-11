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

"""Data structures and algorithms for boolean equations."""

import itertools

from pytypedecl import utils


class BooleanTerm(object):
  """Base class for boolean terms."""

  __new__ = utils.prevent_direct_instantiation

  def simplify(self, assignments):
    """Simplify this term, given a list of possible values for each variable.

    Args:
      assignments: A list of possible values for each variable. A dictionary
        mapping strings (variable name) to sets of strings (value names).

    Returns:
      A new BooleanTerm, potentially simplified.
    """
    raise NotImplementedError()

  def extract_pivots(self):
    """Find variables that appear in every term.

    This searches for variables that appear in all terms of disjunctions, or
    at least one term of conjunctions. These types of variables can be limited
    to the values they appear together with. For example, consider the equation
      t = v1 | (t = v2 & (t = v2 | t = v3))
    Here, t can be limited to [v1, v2]. (v3 is impossible.)

    It's possible for this function to return another variable as the value for
    a given variable. If you don't want that, call simplify() before calling
    extract_pivots().

    Returns:
      A dictionary mapping strings (variable names) to sets of strings (value
      or variable names).
    """
    raise NotImplementedError()


class TrueValue(BooleanTerm):
  """Class for representing "TRUE"."""

  def simplify(self, assignments):
    return self

  def __repr__(self):
    return "TRUE"

  def __str__(self):
    return "TRUE"

  def extract_pivots(self):
    return {}


class FalseValue(BooleanTerm):
  """Class for representing "FALSE"."""

  def simplify(self, assignments):
    return self

  def __repr__(self):
    return "FALSE"

  def __str__(self):
    return "FALSE"

  def extract_pivots(self):
    return {}


TRUE = TrueValue()
FALSE = FalseValue()


class Eq(BooleanTerm):
  """An equality constraint.

  This declares an equality between a variable and a value, or a variable
  and a variable. It's symmetric - constraints with swapped left and right
  compare and hash as if they are equal.

  Attributes:
    left: A string; left side of the equality. This is the string with the
      higher ascii value, so e.g. strings starting with "~" (ascii 0x7e) will be
      on the left.
    right: A string; right side of the equality. This is the lower ascii value.
  """
  __slots__ = ()

  def __new__(cls, left, right):
    """Create an equality or its simplified equivalent.

    This will ensure that left > right. (For left == right, it'll just return
    TRUE).

    Args:
      left: A string. Left side of the equality. This will get sorted, so it
        might end up on the right.
      right: A string. Right side of the equality. This will get sorted, so it
        might end up on the left.

    Returns:
      A BooleanTerm.
    """
    assert isinstance(left, str)
    assert isinstance(right, str)
    if left == right:
      return TRUE
    eq = super(Eq, cls).__new__(cls)
    eq.left, eq.right = reversed(sorted((left, right)))
    return eq

  def __repr__(self):
    return "%s(%r, %r)" % (type(self).__name__, self.left, self.right)

  def __str__(self):
    return "%s == %s" % (self.left, self.right)

  def __hash__(self):
    return hash((self.left, self.right))

  def __eq__(self, other):
    return (type(self) == type(other) and
            self.left == other.left and
            self.right == other.right)

  def __ne__(self, other):
    return not self == other

  def simplify(self, assignments):
    """Simplify this equality.

    This will try to look up the values, and return FALSE if they're no longer
    possible. Also, when comparing two variables, it will compute the
    intersection, and return a disjunction of variable=value equalities instead.

    Args:
      assignments: Variable assignments (dict mapping strings to sets of
      strings). Used to determine whether this equality is still possible, and
      to compute intersections between two variables.

    Returns:
      A new BooleanTerm.
    """
    if (self.right in assignments.get(self.left, ()) or
        self.left in assignments.get(self.right, ())):
      # equality is still possible.
      return self
    intersection = (frozenset(assignments.get(self.left, set())) &
                    frozenset(assignments.get(self.right, set())))
    return Or(And([Eq(self.left, i),
                   Eq(i, self.right)])
              for i in intersection)

  def extract_pivots(self):
    """Extract the pivots. See BooleanTerm.extract_pivots()."""
    return {self.left: frozenset([self.right]),
            self.right: frozenset([self.left])}


class And(BooleanTerm):
  """A conjunction of equalities and disjunctions."""

  def __new__(cls, exprs):
    flattened = itertools.chain.from_iterable(
        e.exprs if isinstance(e, And) else [e] for e in exprs)
    expr_set = frozenset(flattened)
    expr_set -= frozenset([TRUE])  # "x & y & TRUE" is equivalent to "x & y"
    if FALSE in expr_set:
      return FALSE
    if len(expr_set) > 1:
      c = super(And, cls).__new__(cls)
      c.exprs = expr_set
      return c
    elif expr_set:
      expr, = expr_set
      return expr
    else:
      return TRUE  # Empty conjunction is equivalent to True

  def __eq__(self, other):
    return type(self) == type(other) and self.exprs == other.exprs

  def __ne__(self, other):
    return not self == other

  def __repr__(self):
    return "%s%r" % (type(self).__name__, tuple(self.exprs))

  def __str__(self):
    return "(" + " & ".join(str(t) for t in self.exprs) + ")"

  def simplify(self, assignments):
    return And(t.simplify(assignments) for t in self.exprs)

  def extract_pivots(self):
    """Extract the pivots. See BooleanTerm.extract_pivots()."""
    pivots = {}
    for expr in self.exprs:
      expr_pivots = expr.extract_pivots()
      for name, values in expr_pivots.items():
        if name in pivots:
          pivots[name] &= values
        else:
          pivots[name] = values
    return pivots


class Or(BooleanTerm):
  """A disjunction of equalities and conjunctions."""

  def __new__(cls, exprs):
    flattened = itertools.chain.from_iterable(
        e.exprs if isinstance(e, Or) else [e] for e in exprs)
    expr_set = frozenset(flattened)
    expr_set -= frozenset([FALSE])  # "x | y | FALSE" is equivalent to "x | y"
    if TRUE in expr_set:
      return TRUE
    if len(expr_set) > 1:
      d = super(Or, cls).__new__(cls)
      d.exprs = expr_set
      return d
    elif expr_set:
      expr, = expr_set
      return expr
    else:
      return FALSE  # Empty disjunction is equivalent to False

  def __eq__(self, other):  # for unit tests
    return type(self) == type(other) and self.exprs == other.exprs

  def __ne__(self, other):
    return not self == other

  def __repr__(self):
    return "%s%r" % (type(self).__name__, tuple(self.exprs))

  def __str__(self):
    return "(" + " | ".join(str(t) for t in self.exprs) + ")"

  def simplify(self, assignments):
    return Or(t.simplify(assignments) for t in self.exprs)

  def extract_pivots(self):
    """Extract the pivots. See BooleanTerm.extract_pivots()."""
    pivots_list = [expr.extract_pivots() for expr in self.exprs]
    # Extract the names that appear in all subexpressions:
    intersection = frozenset(pivots_list[0].keys())
    for p in pivots_list[1:]:
      intersection &= frozenset(p.keys())
    # Now, for each of the above, collect the list of possible values.
    pivots = {}
    for pivot in intersection:
      values = frozenset()
      for p in pivots_list:
        values |= p[pivot]
      pivots[pivot] = values
    return pivots
