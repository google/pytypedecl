"""Data structures for representing equality constraints between pytd.Classes.
"""

import collections
import functools
import itertools
import logging


from pytypedecl import pytd
from pytypedecl.match import sat_problem


@functools.total_ordering
class Type(object):
  """The base class for constraint types used for matching.

  Attributes:
    structure: the structure of this type as a dict of names to pytd.Functions.
  """

  def IsNominallyCompatibleWith(self, other):
    """True if self and other are compatible nominally."""
    raise NotImplementedError

  @staticmethod
  def FromPyTD(td, complete=True, path=None):
    if isinstance(td, pytd.ClassType):
      if td.cls:
        return ClassType(td.cls, complete)
      else:
        name = str(path or "") + "." + td.name
        return ClassType(pytd.Class(name, (), (), (), ()), False)
    elif isinstance(td, (pytd.HomogeneousContainerType, pytd.GenericType)):
      return Type.FromPyTD(td.base_type)
    elif isinstance(td, pytd.UnionType):
      return UnionType(Type.FromPyTD(t) for t in td.type_list)
    else:
      raise TypeError("Cannot convert: {} ({})".format(td, td.__class__))

  def ToPyTD(self):
    raise NotImplementedError()

  def __gt__(self, other):
    return str(self) < str(other)

  def __eq__(self, other):
    raise NotImplementedError()


class ClassType(Type):
  """A constraint type representing a class."""

  def __init__(self, cls, complete):
    super(ClassType, self).__init__()
    assert isinstance(cls, pytd.Class)
    self.structure = {}
    self.cls = cls
    self.complete = complete
    for func in cls.methods:
      self.structure[func.name] = func

  def IsNominallyCompatibleWith(self, other):
    if isinstance(other, ClassType):
      # TODO(ampere): Check MRO for incomplete classes.
      if self.complete and other.complete:
        return other.cls == self.cls
      else:
        return True
    else:
      return True

  def ToPyTD(self):
    td = pytd.ClassType(self.cls.name)
    td.cls = self.cls
    return td

  def __hash__(self):
    return hash(self.cls)

  def __eq__(self, other):
    if isinstance(other, ClassType):
      return self.cls == other.cls and self.complete == self.complete
    else:
      return False

  def __ne__(self, other):
    return not self == other

  def __repr__(self):
    return "{}{}".format(self.cls.name,
                         "" if self.complete else "#")


def _IntersectStructures(types):
  """Compute the intersection of the structures of several constraint types.

  The intersection of the structures is a map of names to functions such that
  names are only included if they are in all the input types and the functions
  only have signatures that appear for that name in all the types.

  Args:
    types: A sequence of Type objects.
  Returns:
    The intersection of their structure members.
  """
  structure = {}
  structs = [ty.structure for ty in types]
  for name, first_func in structs[0].iteritems():
    if all(name in st for st in structs):
      # TODO(ampere): This is not order preserving, but it's not clear what
      # order to preserve anyway.
      sigs = set(first_func.signatures)
      for st in structs[1:]:
        sigs.intersection_update(st[name].signatures)
      if sigs:
        func = pytd.Function(name, tuple(sigs))
        structure[name] = func
  return structure


class UnionType(Type):
  """A constraint type that is a union of ClassTypes."""

  def __init__(self, subtypes):
    super(UnionType, self).__init__()
    subtypes = frozenset(subtypes)
    assert subtypes
    assert all(isinstance(ty, ClassType) for ty in subtypes)
    self.subtypes = subtypes
    self.complete = all(ty.complete for ty in subtypes)

    self.structure = _IntersectStructures(subtypes)

  def IsNominallyCompatibleWith(self, other):
    # Unions could be the same as anything else because they are not named.
    return True

  def ToPyTD(self):
    return pytd.UnionType(tuple(t.ToPyTD() for t in self.subtypes))

  def __hash__(self):
    return hash(self.subtypes)

  def __eq__(self, other):
    if isinstance(other, UnionType):
      return self.subtypes == other.subtypes
    else:
      return False

  def __ne__(self, other):
    return not self == other

  def __repr__(self):
    return "U{}".format(tuple(self.subtypes))


class Equality(collections.namedtuple("Equality", ["left", "right"])):
  """An equality constraint.

  The constraint is symmetric so constraints with swapped left and right compare
  and hash as if they are equal.
  """
  __slots__ = ()

  def __new__(cls, left, right):
    assert isinstance(left, Type)
    assert isinstance(right, Type)
    return super(Equality, cls).__new__(cls, *sorted((left, right)))

  def __repr__(self):
    return "[{}={}]".format(self.left, self.right)

  def Other(self, v):
    """Return the element that is not v."""
    return self.left if self.right == v else self.right


def Powerset(iterable):
  """powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)."""
  s = list(iterable)
  return itertools.chain.from_iterable(itertools.combinations(s, r)
                                       for r in range(len(s)+1))


class SatEncoder(object):
  """Generate and solve a SAT problem from sets of classes."""

  def __init__(self):
    self.types = set()
    self.sat = sat_problem.SATProblem()

  def _NewEquality(self, a, b):
    self.types.add(a)
    self.types.add(b)
    return Equality(a, b)

  def _SATHint(self, a, b):
    # logging.info("{} ?= {}".format(a, b))
    assert isinstance(a, Equality)
    assert isinstance(b, bool)
    self.sat.Hint(a, b)

  def _SATEqual(self, a, b):
    self.sat.Equals("{} <==> {}".format(a, b), a, b)

  def _SATImplies(self, a, b, nodup=False):
    self.sat.Implies("{} ==> {}".format(a, b), a, b, nodup=nodup)

  def _TypeFromPyTD(self, td, path):
    if isinstance(td, pytd.ClassType):
      matches = [ty for ty in self.types
                 if isinstance(ty, ClassType) and td.name == ty.cls.name]
      if matches:
        ty, = matches  # Fails if there is more than one class with name
        return ty
    return Type.FromPyTD(td, path=path)

  def _SignaturesEqual(self, a, b, a_path=None, b_path=None):
    if len(a.params) == len(b.params):
      param_equalities = []
      for aparam, bparam in zip(a.params, b.params):
        if aparam.type != bparam.type:
          param_equalities.append(self._NewEquality(
              self._TypeFromPyTD(aparam.type, path=a_path),
              self._TypeFromPyTD(bparam.type, path=b_path)))
      if a.return_type != b.return_type:
        return_equalities = [self._NewEquality(
            self._TypeFromPyTD(a.return_type, path=a_path),
            self._TypeFromPyTD(b.return_type, path=b_path))]
      else:
        return_equalities = []
      return sat_problem.Conjunction(itertools.chain(param_equalities,
                                                     return_equalities))
    else:
      return False

  def _FunctionsEqualOneWay(self, left_func, right_func,
                            a_path=None, b_path=None):
    return sat_problem.Conjunction(
        sat_problem.Disjunction(self._SignaturesEqual(left_sig, right_sig,
                                                      a_path, b_path)
                                for right_sig in right_func.signatures)
        for left_sig in left_func.signatures)

  def _GenerateConstraints(self, class_variables):
    for var in class_variables:
      left, right = var
      if not left.IsNominallyCompatibleWith(right):
        self._SATEqual(var, False)
      else:
        conj = set()
        for name in set(left.structure) | set(right.structure):
          if name in left.structure and name in right.structure:
            left_func = left.structure[name]
            right_func = right.structure[name]
            # The path for left is right and the path for right is left. This is
            # because we want to know where a type variables was bound TO not
            # where it was bound FROM.
            if right.complete:
              conj.add(self._FunctionsEqualOneWay(left_func, right_func,
                                                  right, left))
            if left.complete:
              conj.add(self._FunctionsEqualOneWay(right_func, left_func,
                                                  left, right))
          elif (name not in left.structure and left.complete or
                name not in right.structure and right.complete):
            conj.add(False)
            break
        requirement = sat_problem.Conjunction(conj)
        if left.complete and right.complete:
          self._SATEqual(var, requirement)
        else:
          self._SATImplies(var, requirement)
          self._SATHint(var, True)

  def Generate(self, complete_classes, incomplete_classes):
    """Generate the constraints from the given classes.

    Args:
      complete_classes: An iterable of classes that we assume we know everthing
        about.
      incomplete_classes: An iterable of classes we want to match with the
        complete classes.
    """
    class_types = set()
    class_types.update(ClassType(cls, True) for cls in complete_classes)
    class_types.update(ClassType(cls, False) for cls in incomplete_classes)
    class_variables = set(self._NewEquality(*p)
                          for p in itertools.combinations(class_types, 2))
    self.types.update(class_types)
    # self.types.update(UnionType(tys)
    #                   for tys in itertools.combinations(class_types, 2))
    variables = class_variables
    added_variables = variables
    while added_variables:
      self._GenerateConstraints(added_variables)
      new_variables = set(Equality(*p)
                          for p in itertools.combinations(self.types, 2))
      added_variables = new_variables - variables
      logging.warning("New variables: %r", added_variables)
      variables = new_variables

    logging.info("# Types: %r", len(self.types))
    logging.info("# Vars: %r", len(variables))

    logging.debug("Types: %r", self.types)
    logging.debug("Vars: %r", variables)

    use_transitivity_constraints = True
    if use_transitivity_constraints:
      incomplete_types = [t for t in self.types
                          if not t.complete]
      for a in self.types:
        for b in incomplete_types:
          if a == b:
            continue
          for c in self.types:
            if a == c or b == c:
              continue
            eq1 = Equality(a, b)
            eq2 = Equality(b, c)
            eq3 = Equality(a, c)
            assert eq1 in variables
            assert eq2 in variables
            assert eq3 in variables
            self._SATImplies(sat_problem.Conjunction((eq1, eq2)), eq3)

    logging.info("Writing SAT problem")
    for ty in self.types:
      if isinstance(ty, ClassType) and not ty.complete:
        vs = [v for v in variables
              if ty in v and v.Other(ty).complete]
        # logging.info("%r", vs)
        self.sat.BetweenNM("Force assign", vs, 1, None)

  def Solve(self):
    """Solve the constraints generated by calls to generate.

    Returns:
      A map from pytd.Class to pytd.Type that had all the incomplete types that
      can been assigned by the solver.
    """
    self.sat.Solve()
    results = {}
    for var, value in self.sat:
      if value is not False:
        logging.info("%s = %r", var, value)
      if value and isinstance(var, Equality):
        incomp = var.left if not var.left.complete else var.right
        if var.Other(incomp).complete:
          if incomp.cls in results:
            logging.warning("%r is assigned more than once to a complete type: "
                        "%r, %r", incomp, results[incomp.cls],
                        var.Other(incomp))
          results[incomp.cls] = var.Other(incomp).ToPyTD()
    return results
