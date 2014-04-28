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

import collections
import itertools

from pytypedecl import abc_hierarchy
from pytypedecl import pytd


class RemoveDuplicates(object):
  """Remove duplicate function signatures.

  For example, this transforms
    def f(x: int) -> float
    def f(x: int) -> float
  to
    def f(x: int) -> float
  In order to be removed, a signatures has to be exactly identical to an
  existing one.
  """
  # TODO: what if only the argument names differ? Maybe make parser.py
  # output a warning.

  def VisitFunction(self, node):
    # We remove duplicates, but keep entries in the same order.
    ordered_set = collections.OrderedDict(zip(node.signatures, node.signatures))
    return node.Replace(signatures=list(ordered_set))


class _ReturnsAndExceptions(object):
  """Mutable class for collecting return types and exceptions of functions.

  The collecting is stable: Items are kept in the order in which they were
  encountered.
  """

  def __init__(self):
    self.return_types = []
    self.exceptions = []

  def Update(self, signature):
    """Add the return types / exceptions of a signature to this instance."""

    if signature.return_type not in self.return_types:
      self.return_types.append(signature.return_type)

    self.exceptions.extend(exception
                           for exception in signature.exceptions
                           if exception not in self.exceptions)


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
    seen = set()
    new_types = []
    for t in types:
      if isinstance(t, pytd.UnionType):
        types_to_add = t.type_list
      else:
        types_to_add = [t]
      new_types.extend(t for t in types_to_add if t not in seen)
      seen.update(types_to_add)
    return pytd.UnionType(tuple(new_types))


class CombineReturnsAndExceptions(object):
  """Group function signatures that only differ in exceptions or return values.

  For example, this transforms
    def f(x: int) -> float raises OverflowError
    def f(x: int) -> int raises IndexError
  to
    def f(x: int) -> float or int raises IndexError, OverflowError
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
      stripped_signature = sig.Replace(return_type=None, exceptions=None)

      ret = groups.get(stripped_signature)
      if not ret:
        ret = _ReturnsAndExceptions()
        groups[stripped_signature] = ret

      ret.Update(sig)

    return groups

  def VisitFunction(self, f):
    """Merge signatures of a function."""
    groups = self._GroupByArguments(f.signatures)

    new_signatures = []
    for stripped_signature, ret_exc in groups.viewitems():
      ret = JoinTypes(ret_exc.return_types)
      exc = tuple(ret_exc.exceptions)

      new_signatures.append(
          stripped_signature.Replace(return_type=ret, exceptions=exc)
      )
    return f.Replace(signatures=new_signatures)


class ExpandSignatures(object):
  """Remove parameters with multiple types, by splitting functions in two.

  For example, this transforms
    def f(x: int or float, y: int or float)
  to
    def f(x: int, y: int)
    def f(x: int, y: float)
    def f(x: float, y: int)
    def f(x: float, y: float)

  This is also called the "cartesian product".  The expansion by this class
  is typically *not* an optimization. But it can be the precursor for
  optimizations that need the expanded signatures, or it can simplify code
  generation, like generating type declarations for a type inferencer.
  """

  def VisitFunction(self, f):
    """Rebuild the function with the new signatures."""

    # concatenate return value(s) from VisitSignature
    new_signatures = tuple(sum(f.signatures, []))

    return f.Replace(signatures=new_signatures)

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

    new_signatures = [sig.Replace(params=tuple(combination))
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
      stripped_signature = sig.Replace(params=tuple(params))
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
          sig = sig.Replace(params=tuple(new_params))
          new_sigs.append(sig)
      signatures = new_sigs

    return f.Replace(signatures=tuple(signatures))


class ApplyOptionalArguments(object):
  """Removes functions that are instances of a more specific case.

  For example, this reduces
    def f(x: int, ...)
    def f(x: int, y: int)
  to just
    def f(x: int, ...)

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
      shortened = sig.Replace(params=sig.params[0:i], has_optional=True)
      if shortened in optional_arg_sigs:
        return True

  def VisitFunction(self, f):
    """Remove all signatures that have a shorter version."""

    # Set of signatures that can replace longer ones. Only used for matching,
    # hence we can use an unordered data structure.
    optional_arg_sigs = frozenset(s for s in f.signatures if s.has_optional)

    new_signatures = [s for s in f.signatures
                      if not self._HasShorterVersion(s, optional_arg_sigs)]
    return f.Replace(signatures=tuple(new_signatures))


class FindCommonSuperClasses(object):
  """Find common super classes.

  E.g., this changes
    def f(x: list or tuple, y: frozenset or set) -> int or float
  to
    def f(x: Sequence, y: Set) -> Real
  """

  def __init__(self):
    self._superclasses = abc_hierarchy.GetSuperClasses()
    self._subclasses = abc_hierarchy.GetSubClasses()

  # TODO: This only works for built-in types so far. Make this work for
  # class hierarchy extracted from pytd as well?

  def _CollectSuperclasses(self, node, collect):
    """Recursively collect super classes for a type.

    Args:
      node: A type node.
      collect: A set(), modified to contain all superclasses.
    """
    collect.add(node)
    superclasses = [pytd.NamedType(name)
                    for name in self._superclasses.get(str(node), [])]

    if node != pytd.NamedType("object"):
      # Everything but object itself subclasses object. This is not explicitly
      # specified in _superclasses, so we add object manually.
      superclasses.append(pytd.NamedType("object"))

    # The superclasses might have superclasses of their own, so recurse.
    for superclass in superclasses:
      self._CollectSuperclasses(superclass, collect)

  def _Expand(self, t):
    """Generate a list of all (known) superclasses for a type.

    Args:
      t: A type.

    Returns:
      A set of types. This set includes t as well as all its superclasses.
    """
    superclasses = set()
    self._CollectSuperclasses(t, superclasses)
    return superclasses

  def _HasSubClassInSet(self, cls, known):
    """Queries whether a subclass of a type is present in a given set."""

    # object is an implicit superclass of all types. So if we're being asked
    # whether object has a subclass in the set, we just need to find any
    # class that's not object itself.
    if (cls == pytd.NamedType("object")
        and known
        and any(k == pytd.NamedType("object") for k in known)):
      return True

    return any(pytd.NamedType(sub) in known
               for sub in self._subclasses[str(cls)])

  def VisitUnionType(self, union):
    """Given a union type, try to find a simplification through ABCs.

    This function tries to map a list of types to a common base type. For
    example, [int, float] are both (abstract) base classes of Real, so
    it would convert UnionType([int, float]) to BaseType(Real).

    Args:
      union: A union type.

    Returns:
      A simplified type, if available.
    """
    intersection = self._Expand(union.type_list[0])

    for t in union.type_list[1:]:
      intersection.intersection_update(self._Expand(t))

    # Remove "redundant" superclasses, by removing everything from the tree
    # that's not a leaf. I.e., we don't need "object" if we have more
    # specialized types.
    new_type_list = tuple(cls for cls in intersection
                          if not self._HasSubClassInSet(cls, intersection))

    return JoinTypes(new_type_list)


class ShortenUnions(object):
  """Shortens long unions to object.

  Poor man's version of FindCommonSuperClasses. Some signature extractions
  generate signatures like
    class str:
      def __init__(self, obj: str or unicode or int or float or list)
  We shorten that to
    class str:
      def __init__(self, obj: object)
  In other words, if there are too many types "or"ed together, we just replace
  the entire thing with "object".
  Additionally, if the union already contains at least one "object", we also
  replace the entire union with just "object".

  Attributes:
    max_length: The maximum number of types to allow in a union. If there are
      more types than this (or the union contains "object"), we use "object"
      for everything instead.  The current (experimental) default for this
      parameter is four, so only up to four types can be represented as a union.
  """

  def __init__(self, max_length=4):
    self.max_length = max_length

  def VisitUnionType(self, union):
    if len(union.type_list) > self.max_length:
      return pytd.NamedType("object")
    elif pytd.NamedType("object") in union.type_list:
      return pytd.NamedType("object")
    else:
      return union


def Optimize(node):
  """Optimize a PYTD tree."""
  node = node.Visit(RemoveDuplicates())
  node = node.Visit(CombineReturnsAndExceptions())
  node = node.Visit(Factorize())
  node = node.Visit(ApplyOptionalArguments())
  node = node.Visit(ShortenUnions())
  return node

