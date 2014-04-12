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


def JoinTypes(types):
  """Combine a list of types into a union type, if needed.

  Leave singular return values alone, and wraps a UnionType around them if there
  are multiple ones.

  Args:
    types: A list of types. This list might contain other UnionTypes. If
    so, they are flattened.

  Returns:
    A type that represents the union of the types passed in.
  """
  assert types

  if len(types) == 1:
    return types[0]
  else:
    new_types = []
    for t in types:
      if isinstance(t, pytd.UnionType):
        new_types += t.type_list
      else:
        new_types.append(t)
    return pytd.UnionType(tuple(new_types))


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

      # TODO: Do we need the sorting? It would be nicer if this
      #              was a stable operation that didn't change the order.
      ret = JoinTypes(sorted(return_types))

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


class Factorize(object):
  """Opposite of ExpandSignatures. Factorizes cartesian products of functions.

  For example, this transforms
    def f(x: int, y: int)
    def f(x: int, y: float)
    def f(x: float, y: int)
    def f(x: float, y: float)
  to
    def f(x: int or float, y: int or float)
  .
  """

  def _GroupByOmittedArg(self, signatures, i):
    """Group functions that are identical if you ignore one of the arguments.

    Args:
      signatures: A list of function signatures
      i: The index of the argument to ignore during comparison.

    Returns:
      A list of tuples (signature, types). "signature" are signatures where
      argument i is omitted, "types" is a list of types that argument was
      found to have. signatures that don't have argument i are represented
      as (original, None).
    """
    groups = collections.OrderedDict()
    for sig in signatures:
      if i >= len(sig.params):
        # We can't omit argument i, because this signature doesn't have that
        # many arguments. Represent this signature as (original, None).
        groups[sig] = None
        continue
      params = list(sig.params)
      param_i = params[i]
      params[i] = pytd.Parameter(param_i.name, None)
      stripped_signature = sig._replace(params=tuple(params))
      existing = groups.get(stripped_signature)
      if not existing:
        groups[stripped_signature] = [param_i.type]
      else:
        existing.append(param_i.type)
    return groups.items()

  def VisitFunction(self, f):
    """Shrink a function, by factorizing cartesian products of arguments."""
    max_argument_count = max(len(s.params) for s in f.signatures)
    signatures = f.signatures

    # Greedily group signatures, looking at the arguments from left to right.
    # This algorithm is *not* optimal. But it does the right thing for the
    # typical cases.
    for i in range(max_argument_count):
      new_sigs = []
      for sig, types in self._GroupByOmittedArg(signatures, i):
        if types is None:
          # A signature that doesn't have argument <i>
          new_sigs.append(sig)
        else:
          # A signature that has one or more options for argument <i>
          new_params = list(sig.params)
          new_params[i] = pytd.Parameter(sig.params[i].name, JoinTypes(types))
          sig = sig._replace(params=tuple(new_params))
          new_sigs.append(sig)
      signatures = new_sigs

    return f._replace(signatures=tuple(signatures))


class ApplyOptionalArguments(object):
  """Removes functions that are instances of a more specific case.

  For example, this reduces
    def f(x: int, ...)
    def f(x: int, y: int)
  to just
    def f(x: int, ...)
  .
  Because "..." makes it possible to pass any additional arguments, the latter
  encompasses both declarations, one of which can hence be omitted.
  """

  def _HasShorterVersion(self, sig, optional_arg_sigs):
    """Find a shorter signature with optional arguments of a longer signature.

    Args:
      sig: The function signature we'd like to shorten
      optional_arg_sigs: A list of function signatures with optional arguments
        that will be matched against sig.

    Returns:
      True if there is a shorter signature that generalizes sig.
    """

    param_count = len(sig.params)

    if not sig.has_optional:
      param_count += 1  # also consider f(x, y, ...) for f(x, y)

    for i in xrange(param_count):
      shortened = sig._replace(params=sig.params[0:i], has_optional=True)
      if shortened in optional_arg_sigs:
        return True

  def VisitFunction(self, f):
    """Remove all signatures that have a shorter version."""
    optional_arg_sigs = set(s for s in f.signatures if s.has_optional)
    new_signatures = [s for s in f.signatures
                      if not self._HasShorterVersion(s, optional_arg_sigs)]
    return f._replace(signatures=tuple(new_signatures))


def Optimize(node):
  """Optimize a PYTD tree."""
  node = node.Visit(RemoveDuplicates())
  node = node.Visit(CombineReturnsAndExceptions())
  node = node.Visit(Factorize())
  node = node.Visit(ApplyOptionalArguments())
  return node

