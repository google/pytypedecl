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


"""Functions for optimizing pytd parse trees and ASTs."""

# For namedtuple._replace (TODO: Rename this in node.py):
# pylint: disable=protected-access

import collections
import itertools

from pytypedecl import pytd


class RemoveDuplicates(object):
  """Remove duplicate function signatures.

  For example, this transforms
    def f(x: int) -> float
    def f(x: int) -> float
  to
    def f(x: int) -> float
  .
  In order to be removed, a signatures has to be exactly identical to an
  existing one.
  """
  # TODO: what if only the argument names differ? Maybe make parser.py
  # output a warning.

  def VisitFunction(self, node):
    # We remove duplicates, but keep entries in the same order.
    ordered_set = collections.OrderedDict(zip(node.signatures, node.signatures))
    return node._replace(signatures=list(ordered_set))


ReturnsAndExceptions = collections.namedtuple(
    "ReturnsAndExceptions", ["return_types", "exceptions"])


class CombineReturnsAndExceptions(object):
  """Group function signatures that only differ in exceptions or return values.

  For example, this transforms
    def f(x: int) -> float raises OverflowError
    def f(x: int) -> int raises IndexError
  to
    def f(x: int) -> float or int raises IndexError, OverflowError
  .
  """

  def _GroupByArguments(self, signatures):
    """Groups signatures by arguments.

    Args:
      signatures: A list of function signatures (Signature instances).

    Returns:
      A dictionary mapping signatures (without return and exceptions) to
      a tuple of return values and exceptions.
    """
    groups = collections.OrderedDict()
    for sig in signatures:
      stripped_signature = sig._replace(return_type=None, exceptions=None)
      existing = groups.get(stripped_signature)
      if existing:
        existing.return_types.add(sig.return_type)
        existing.exceptions.update(sig.exceptions)
      else:
        groups[stripped_signature] = ReturnsAndExceptions(
            set([sig.return_type]), set(sig.exceptions))
    return groups

  def VisitFunction(self, f):
    """Merge signatures of a function."""
    groups = self._GroupByArguments(f.signatures)

    new_signatures = []
    for stripped_signature, ret_and_exc in groups.viewitems():
      return_types, exceptions = ret_and_exc

      # We leave singular return values alone, and wrap a union type
      # if there are multiple ones.
      if len(return_types) == 1:
        ret, = list(return_types)
      else:
        ret = pytd.UnionType(tuple(sorted(return_types)))

      # TODO: Once we change Signature.exceptions to be a single type
      #              instead of a list, make this return a union type.
      exc = tuple(sorted(exceptions))

      new_signatures.append(
          stripped_signature._replace(return_type=ret, exceptions=exc)
      )
    return f._replace(signatures=new_signatures)


class ExpandSignatures(object):
  """Remove parameters with multiple types, by splitting functions in two.

  For example, this transforms
    def f(x: int or float, y: int or float)
  to
    def f(x: int, y: int)
    def f(x: int, y: float)
    def f(x: float, y: int)
    def f(x: float, y: float)
  .
  This is also called the "cartesian product".  The expansion by this class
  is typically *not* an optimization. But it can be the precursor for
  optimizations that need the expanded signatures, or it can simplify code
  generation, like generating type declarations for a type inferencer.
  """

  def VisitFunction(self, f):
    """Rebuild the function with the new signatures."""
    new_signatures = []
    for signature in f.signatures:
      if isinstance(signature, list):
        # signature that got expanded
        new_signatures += signature
      else:
        # single signature we didn't touch
        new_signatures.append(signature)
    return f._replace(signatures=tuple(new_signatures))

  def VisitSignature(self, sig):
    """Expand a single signature."""
    params = []
    # TODO: This doesn't take nested types like ((a or b) or c) into
    #              account. Maybe we need a visitor that flattens structures
    #              like that beforehand.
    for name, param_type in sig.params:
      if isinstance(param_type, pytd.UnionType):
        # multiple types
        params.append([pytd.Parameter(name, t) for t in param_type.type_list])
      else:
        # single type
        params.append([pytd.Parameter(name, param_type)])

    new_signatures = [sig._replace(params=tuple(combination))
                      for combination in itertools.product(*params)]

    return new_signatures  # Hand list over to VisitFunction


def Optimize(node):
  """Optimize a PYTD tree."""
  node = node.Visit(RemoveDuplicates())
  node = node.Visit(CombineReturnsAndExceptions())
  return node

