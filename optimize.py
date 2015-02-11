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


"""Functions for optimizing pytd syntax trees.

   pytd files come from various sources, and are typically redundant (duplicate
   functions, different signatures saying the same thing, overlong type
   disjunctions). The Visitors in this file remove various forms of these
   redundancies.
"""

import collections
import itertools

from pytypedecl import abc_hierarchy
from pytypedecl import pytd
from pytypedecl.parse import visitors


class RemoveDuplicates(object):
  """Remove duplicate function signatures.

  For example, this transforms
    def f(x: int) -> float
    def f(x: int) -> float
  to
    def f(x: int) -> float
  In order to be removed, a signature has to be exactly identical to an
  existing one.
  """

  def VisitFunction(self, node):
    # We remove duplicates, but keep existing entries in the same order.
    ordered_set = collections.OrderedDict(zip(node.signatures, node.signatures))
    return node.Replace(signatures=list(ordered_set))


class _ReturnsAndExceptions(object):
  """Mutable class for collecting return types and exceptions of functions.

  The collecting is stable: Items are kept in the order in which they were
  encountered.

  Attributes:
    return_types: Return types seen so far.
    exceptions: Exceptions seen so far.
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

  Leaves singular return values alone, or wraps a UnionType around them if there
  are multiple ones, or if there are no elements in the list (or only
  NothingType) return NothingType.

  Arguments:
    types: A list of types. This list might contain other UnionTypes. If
    so, they are flattened.

  Returns:
    A type that represents the union of the types passed in. Order is preserved.
  """
  queue = collections.deque(types)
  seen = set()
  new_types = []
  while queue:
    t = queue.popleft()
    if isinstance(t, pytd.UnionType):
      queue.extendleft(reversed(t.type_list))
    elif isinstance(t, pytd.NothingType):
      pass
    elif t not in seen:
      new_types.append(t)
      seen.add(t)

  if len(new_types) == 1:
    return new_types.pop()
  elif any(isinstance(t, pytd.UnknownType) for t in new_types):
    return pytd.UnknownType()
  elif new_types:
    return pytd.UnionType(tuple(new_types))  # tuple() to make unions hashable
  else:
    return pytd.NothingType()


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

    Arguments:
      signatures: A list of function signatures (Signature instances).

    Returns:
      A dictionary mapping signatures (without return and exceptions) to
      a tuple of return values and exceptions.
    """
    groups = collections.OrderedDict()  # Signature -> ReturnsAndExceptions
    for sig in signatures:
      stripped_signature = sig.Replace(return_type=None, exceptions=None)

      ret = groups.get(stripped_signature)
      if not ret:
        ret = _ReturnsAndExceptions()
        groups[stripped_signature] = ret

      ret.Update(sig)

    return groups

  def VisitFunction(self, f):
    """Merge signatures of a function.

    This groups signatures by arguments and then for each group creates a
    single signature that joins the return values / exceptions using "or".

    Arguments:
      f: A pytd.Function instance

    Returns:
      Function with simplified / combined signatures.
    """
    groups = self._GroupByArguments(f.signatures)

    new_signatures = []
    for stripped_signature, ret_exc in groups.items():
      ret = JoinTypes(ret_exc.return_types)
      exc = tuple(ret_exc.exceptions)

      new_signatures.append(
          stripped_signature.Replace(return_type=ret, exceptions=exc)
      )
    return f.Replace(signatures=new_signatures)


class CombineContainers(object):
  """Change unions of containers to containers of unions.

  For example, this transforms
    list<int> or list<float>
  to
    list<int or float>
  .
  """

  def VisitUnionType(self, union):
    """Push unions down into containers.

    This collects similar container types in unions and merges them into
    single instances with the union type pushed down to the element_type level.

    Arguments:
      union: A pytd.Union instance

    Returns:
      A simplified pytd.Union.
    """
    if not any(isinstance(t, pytd.HomogeneousContainerType)
               for t in union.type_list):
      # Optimization: If we're not going to change anything, return original.
      return union
    union = JoinTypes(union.type_list)  # flatten
    collect = {}
    for t in union.type_list:
      if isinstance(t, pytd.HomogeneousContainerType):
        if t.base_type in collect:
          collect[t.base_type] = JoinTypes(
              [collect[t.base_type], t.element_type])
        else:
          collect[t.base_type] = t.element_type
    result = pytd.NothingType()
    for t in union.type_list:
      if isinstance(t, pytd.HomogeneousContainerType):
        if t.base_type not in collect:
          continue  # already added
        add = t.Replace(parameters=(collect[t.base_type],))
        del collect[t.base_type]
      else:
        add = t
      result = JoinTypes([result, add])
    return result


class ExpandSignatures(object):
  """Expand to Cartesian product of parameter types.

  For example, this transforms
    def f(x: int or float, y: int or float)
  to
    def f(x: int, y: int)
    def f(x: int, y: float)
    def f(x: float, y: int)
    def f(x: float, y: float)

  The expansion by this class is typically *not* an optimization. But it can be
  the precursor for optimizations that need the expanded signatures, and it can
  simplify code generation, e.g. when generating type declarations for a type
  inferencer.
  """

  def VisitFunction(self, f):
    """Rebuild the function with the new signatures.

    This is called after its children (i.e. when VisitSignature has already
    converted each signature into a list) and rebuilds the function using the
    new signatures.

    Arguments:
      f: A pytd.Function instance.

    Returns:
      Function with the new signatures.
    """

    # concatenate return value(s) from VisitSignature
    new_signatures = tuple(sum(f.signatures, []))

    return f.Replace(signatures=new_signatures)

  def VisitSignature(self, sig):
    """Expand a single signature.

    For argument lists that contain disjunctions, generates all combinations
    of arguments. The expansion will be done right to left.
    E.g., from (a or b, c or d), this will generate the signatures
    (a, c), (a, d), (b, c), (b, d). (In that order)

    Arguments:
      sig: A pytd.Signature instance.

    Returns:
      A list. The visit function of the parent of this node (VisitFunction) will
      process this list further.
    """
    params = []
    for param in sig.params:
      # To make this work with MutableParameter
      name, param_type = param.name, param.type
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

    Arguments:
      signatures: A list of function signatures
      i: The index of the argument to ignore during comparison.

    Returns:
      A list of tuples (signature, types). "signature" is a signature with
      argument i omitted, "types" is the list of types that argument was
      found to have. signatures that don't have argument i are represented
      as (original, None).
    """
    groups = collections.OrderedDict()
    for sig in signatures:
      if i >= len(sig.params):
        # We can't omit argument i, because this signature has too few
        # arguments. Represent this signature as (original, None).
        groups[sig] = None
        continue

      # Set type of parameter i to None
      params = list(sig.params)
      param_i = params[i]
      params[i] = pytd.Parameter(param_i.name, None)

      stripped_signature = sig.Replace(params=tuple(params))
      existing = groups.get(stripped_signature)
      if existing:
        existing.append(param_i.type)
      else:
        groups[stripped_signature] = [param_i.type]
    return groups.items()

  def VisitFunction(self, f):
    """Shrink a function, by factorizing cartesian products of arguments.

    Greedily groups signatures, looking at the arguments from left to right.
    This algorithm is *not* optimal. But it does the right thing for the
    typical cases.

    Arguments:
      f: An instance of pytd.Function. If this function has more than one
          signature, we will try to combine some of these signatures by
          introducing union types.

    Returns:
      A new, potentially optimized, instance of pytd.Function.
    """
    max_argument_count = max(len(s.params) for s in f.signatures)
    signatures = f.signatures

    for i in xrange(max_argument_count):
      new_sigs = []
      for sig, types in self._GroupByOmittedArg(signatures, i):
        if types:
          # One or more options for argument <i>:
          new_params = list(sig.params)
          new_params[i] = pytd.Parameter(sig.params[i].name, JoinTypes(types))
          sig = sig.Replace(params=tuple(new_params))
          new_sigs.append(sig)
        else:
          # Signature doesn't have argument <i>, so we store the original:
          new_sigs.append(sig)
      signatures = new_sigs

    return f.Replace(signatures=tuple(signatures))


class ApplyOptionalArguments(object):
  """Removes functions that are instances of a more specific case.

  For example, this reduces
    def f(x: int, ...)    # [1]
    def f(x: int, y: int) # [2]
  to just
    def f(x: int, ...)

  Because "..." makes it possible to pass any additional arguments to [1],
  it encompasses both declarations, hence we can omit [2].
  """

  def _HasShorterVersion(self, sig, optional_arg_sigs):
    """Find a shorter signature with optional arguments for a longer signature.

    Arguments:
      sig: The function signature we'd like to shorten
      optional_arg_sigs: A set of function signatures with optional arguments
        that will be matched against sig.

    Returns:
      True if there is a shorter signature that generalizes sig, but is not
          identical to sig.
    """

    param_count = len(sig.params)

    if not sig.has_optional:
      param_count += 1  # also consider f(x, y, ...) for f(x, y)

    for i in xrange(param_count):
      shortened = sig.Replace(params=sig.params[0:i], has_optional=True)
      if shortened in optional_arg_sigs:
        return True
    return False

  def VisitFunction(self, f):
    """Remove all signatures that have a shorter version.

    We use signatures with optional argument (has_opt=True) as template
    and then match all signatures against those templates, removing those
    that match.

    Arguments:
      f: An instance of pytd.Function

    Returns:
      A potentially simplified instance of pytd.Function.
    """

    # Set of signatures that can replace longer ones. Only used for matching,
    # hence we can use an unordered data structure.
    optional_arg_sigs = frozenset(s for s in f.signatures if s.has_optional)

    new_signatures = (s for s in f.signatures
                      if not self._HasShorterVersion(s, optional_arg_sigs))
    return f.Replace(signatures=tuple(new_signatures))


class FindCommonSuperClasses(object):
  """Find common super classes. Optionally also uses abstract base classes.

  E.g., this changes
    def f(x: list or tuple, y: frozenset or set) -> int or float
  to
    def f(x: Sequence, y: Set) -> Real
  """

  def __init__(self, superclasses=None, use_abcs=True):
    self._superclasses = superclasses or {}
    self._subclasses = abc_hierarchy.Invert(self._superclasses)
    if use_abcs:
      self._superclasses.update(abc_hierarchy.GetSuperClasses())
      self._subclasses.update(abc_hierarchy.GetSubClasses())

  def _CollectSuperclasses(self, node, collect):
    """Recursively collect super classes for a type.

    Arguments:
      node: A type node.
      collect: A set(), modified to contain all superclasses.
    """
    collect.add(node)
    superclasses = [pytd.NamedType(name)
                    for name in self._superclasses.get(str(node), [])]

    # The superclasses might have superclasses of their own, so recurse.
    for superclass in superclasses:
      self._CollectSuperclasses(superclass, collect)

    if node != pytd.NamedType("object"):
      # Everything but object itself subclasses object. This is not explicitly
      # specified in _superclasses, so we add object manually.
      collect.add(pytd.NamedType("object"))

  def _Expand(self, t):
    """Generate a list of all (known) superclasses for a type.

    Arguments:
      t: A type. E.g. NamedType("int").

    Returns:
      A set of types. This set includes t as well as all its superclasses. For
      example, this will return "bool", "int" and "object" for "bool".
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
        and any(k != pytd.NamedType("object") for k in known)):
      return True

    return any(pytd.NamedType(sub) in known
               for sub in self._subclasses[str(cls)])

  def VisitUnionType(self, union):
    """Given a union type, try to find a simplification by using superclasses.

    This is a lossy optimization that tries to map a list of types to a common
    base type. For example, int and bool are both base classes of int, so it
    would convert "int or bool" to "int".

    Arguments:
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

  Poor man's version of FindCommonSuperClasses. Shorten types like
  "str or unicode or int or float or list" to just "object".

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


class ShortenParameterUnions(object):
  """Shortens long unions in parameters to object.

  This is a lossy optimization that changes overlong disjunctions in arguments
  to just "object".
  Some signature extractions generate signatures like
    class str:
      def __init__(self, obj: str or unicode or int or float or list)
  We shorten that to
    class str:
      def __init__(self, obj: object)
  In other words, if there are too many types "or"ed together, we just replace
  the entire thing with "object".

  Attributes:
    max_length: The maximum number of types to allow in a parameter. See
      ShortenUnions.
  """

  def __init__(self, max_length=4):
    self.max_length = max_length

  def VisitParameter(self, param):
    return param.Visit(ShortenUnions())


class PullInMethodClasses(object):
  """Simplifies classes with only a __call__ function to just a method.

  This transforms
    class Foo:
      m: Bar
    class Bar:
      def __call__(self: Foo, ...)
  to
    class Foo:
      def m(self, ...)
  .
  """

  def __init__(self):
    self._module = None
    self._total_count = collections.defaultdict(int)
    self._processed_count = collections.defaultdict(int)

  def _MaybeLookup(self, t):
    if isinstance(t, pytd.NamedType):
      try:
        return self._module.Lookup(t.name)
      except KeyError:
        return None
    elif isinstance(t, pytd.ClassType):
      return t.cls
    else:
      return None

  def _HasSelf(self, sig):
    """True if a signature has a self parameter.

    This only checks for the name, since the type can be too many different
    things (type of the method, type of the parent class, object, unknown etc.)
    and doesn't carry over to the simplified version, anyway.

    Arguments:
      sig: Function signature (instance of pytd.Signature)
    Returns:
      True if the signature has "self".
    """
    return sig.params and sig.params[0].name == "self"

  def _IsSimpleCall(self, t):
    """Returns whether a type has only one method, "__call__"."""
    if not isinstance(t, (pytd.NamedType, pytd.ClassType)):
      # We only do this for simple types.
      return False
    cls = self._MaybeLookup(t)
    if not cls:
      # We don't know this class, so assume it's not a method.
      return False
    if [f.name for f in cls.methods] != ["__call__"]:
      return False
    method, = cls.methods
    return all(self._HasSelf(sig)
               for sig in method.signatures)

  def _CanDelete(self, cls):
    """Checks whether this class can be deleted.

    Returns whether all occurences of this class as a type were due to
    constants we removed.

    Arguments:
      cls: A pytd.Class.
    Returns:
      True if we can delete this class.
    """
    if not self._processed_count[cls.name]:
      # Leave standalone classes alone. E.g. the pytd files in
      # pytypedecl/builtins/ defines classes not used by anything else.
      return False
    return self._processed_count[cls.name] == self._total_count[cls.name]

  def EnterTypeDeclUnit(self, module):
    # Since modules are hierarchical, we enter TypeDeclUnits multiple times-
    # but we only want to record the top-level one.
    if not self._module:
      self._module = module

  def VisitTypeDeclUnit(self, unit):
    return unit.Replace(classes=tuple(c for c in unit.classes
                                      if not self._CanDelete(c)))

  def VisitClassType(self, t):
    self._total_count[t.name] += 1
    return t

  def VisitNamedType(self, t):
    self._total_count[t.name] += 1
    return t

  def VisitClass(self, cls):
    """Visit a class, and change constants to methods where possible."""
    new_constants = []
    new_methods = list(cls.methods)
    for const in cls.constants:
      if self._IsSimpleCall(const.type):
        c = self._MaybeLookup(const.type)
        signatures = c.methods[0].signatures
        self._processed_count[c.name] += 1
        new_methods.append(
            pytd.Function(const.name, signatures))
      else:
        new_constants.append(const)  # keep
    cls = cls.Replace(constants=new_constants,
                      methods=new_methods)
    return cls.Visit(visitors.AdjustSelf(force=True))


OptimizeFlags = collections.namedtuple("_", ["lossy", "use_abcs", "max_union"])


def Optimize(node, flags=None):
  """Optimize a PYTD tree.

  Tries to shrink a PYTD tree by applying various optimizations.

  Arguments:
    node: A pytd node to be optimized. It won't be modified - this function will
        return a new node.
    flags: An instance of OptimizeFlags, to control which optimizations
        happen and what parameters to use for the ones that take parameters. Can
        be None, in which case defaults will be applied.

  Returns:
    An optimized node.
  """
  node = node.Visit(RemoveDuplicates())
  node = node.Visit(CombineReturnsAndExceptions())
  node = node.Visit(Factorize())
  node = node.Visit(ApplyOptionalArguments())
  node = node.Visit(CombineContainers())
  if flags and flags.lossy:
    hierarchy = node.Visit(visitors.ExtractSuperClasses())
    node = node.Visit(
        FindCommonSuperClasses(hierarchy, flags and flags.use_abcs)
    )
    node = node.Visit(ShortenParameterUnions(flags and flags.max_union))
  return node
