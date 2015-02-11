"""A simplified API to the Paris SAT solver.

SATProblem allows you to add certain kinds of expressions to the SAT
problem. The expressions are represented as nested Conjunctions and Disjunctions
with True/False used directly as booleans and any other object treated as a
variable name.
"""

import collections
import logging
import os
import subprocess
import tempfile


from pytypedecl import utils



def GetSatRunnerBinary():
  return "sat_runner"  # pylint: disable=unreachable


class Conjunction(collections.namedtuple("Conjunction", ["exprs"])):
  """A conjunction of variables or other expressions.

  This never contains boolean constants.
  """

  def __new__(cls, exprs):
    expr_set = frozenset(
        sum((list(expr.exprs) if isinstance(expr, Conjunction)
             else [expr]
             for expr in exprs), [])) - frozenset([True])
    if False in expr_set:
      return False
    if len(expr_set) > 1:
      return super(Conjunction, cls).__new__(cls, expr_set)
    elif expr_set:
      expr, = expr_set
      return expr
    else:
      return True  # Empty conjunction is equivalent to True

  __slots__ = ()

  def __eq__(self, other):  # for unit tests
    return type(self) == type(other) and self.exprs == other.exprs

  def __ne__(self, other):
    return not (self == other)

  # __hash__(self) uses tuple.__hash__, which is "good enough"

  def __str__(self):
    return "(" + " & ".join(str(t) for t in self.exprs) + ")"


class Disjunction(collections.namedtuple("Disjunction", ["exprs"])):
  """A disjunction of variables or other expressions.

  This never contains boolean constants.
  """

  def __new__(cls, exprs):
    expr_set = frozenset(
        sum((list(expr.exprs) if isinstance(expr, Disjunction)
             else [expr]
             for expr in exprs), [])) - frozenset([False])
    if True in expr_set:
      return True
    if len(expr_set) > 1:
      return super(Disjunction, cls).__new__(cls, frozenset(expr_set))
    elif expr_set:
      expr, = expr_set
      return expr
    else:
      return False  # Empty disjunction is equivalent to False

  __slots__ = ()

  def __eq__(self, other):  # for unit tests
    return type(self) == type(other) and self.exprs == other.exprs

  def __ne__(self, other):
    return not (self == other)

  # __hash__(self) uses tuple.__hash__, which is "good enough"

  def __str__(self):
    return "(" + " | ".join(str(t) for t in self.exprs) + ")"


class SATProblem(object):
  """A simplified SAT solver interface.

  This implements a dict-like interface, allowing iteration over the results, or
  selecting an individual result by name.
  """

  def __init__(self, name="", initial_polarity=True):
    pb = boolean_problem_pb2
    problem = pb.LinearBooleanProblem()
    problem.name = name
    self.initial_polarity = initial_polarity
    self.problem = problem
    self.constraints = set()
    self._next_id = 1
    self._id_table = {}
    self._results = {}
    self._variables = []

  def __getitem__(self, var):
    return self._results[var]

  def __iter__(self):
    return self._results.iteritems()

  def __repr__(self):
    return ("{type}("
            "initial_polarity={s.initial_polarity}, "
            "_next_id={s._next_id}, "
            "_variables={s._variables}, "
            "problem={s.problem!s}, "
            "constraints={s.constraints!r}, "
            "_results={s._results!r}"
            ")").format(type=type(self).__name__,
                        s=self)

  def Solve(self):
    """Solve the SAT problem that has been created by calling methods on self.
    The result is available by self[var] or iterating over self
    """
    logging.info("%d formulae, %d variables",
                 len(self.problem.constraints), len(self._variables))
    self.problem.num_variables = self._next_id - 1
    # We don't actually need variable names in the buffer, so leave them out to
    # save space.
    # self.problem.var_names.extend(str(v) for v in self._variables)
    if logging.getLogger().isEnabledFor(logging.DEBUG):
      for i, var in enumerate(self._variables):
        logging.debug("%d: %r", i + 1, var)

    logging.info("Storing SAT problem buffer")
    with tempfile.NamedTemporaryFile(delete=False, mode="wb") as fi:
      fi.write(self.problem.SerializeToString())
      problemfile = fi.name

    logging.info("Solving: %r", problemfile)
    tmpdir = os.environ.get("TEST_TMPDIR", None) or (
             os.environ.get("TMPDIR", None))
    with tempfile.NamedTemporaryFile(delete=False, dir=tmpdir) as solutionfi:
      solutionfi.write("")
      solutionfile = solutionfi.name
    commandline = [GetSatRunnerBinary()]
    if logging.getLogger().isEnabledFor(logging.INFO):
      commandline.append("-logtostderr")
    if self.initial_polarity:
      commandline.extend(["-params", "initial_polarity:0"])
    commandline.extend([
        "-input=" + problemfile,
        "-output=" + solutionfile,
        "-use_lp_proto=false"])
    solution = None

    try:
      subprocess.check_call(commandline)
      logging.info("Loading SAT problem buffer: %r", solutionfile)
      solution = boolean_problem_pb2.LinearBooleanProblem()
      with open(solutionfile, "rb") as fi:
        solution.ParseFromString(fi.read())
      self._results = {v: None for v in self._variables}
      if not solution.assignment.literals and self._variables:
        logging.error("SAT solver failed.")
        self._results = {}
        return
      for varid in solution.assignment.literals:
        self._results[self._variables[abs(varid) - 1]] = varid > 0
    except subprocess.CalledProcessError:
      logging.error("SAT solver failed. Probably UNSAT, returning the empty "
                    "result.", exc_info=True)
      self._results = {}
      return
    finally:
      if logging.getLogger().isEnabledFor(logging.DEBUG):
        if solution and solution.HasField("assignment"):
          logging.debug(text_format.MessageToString(solution))
        else:
          logging.debug(text_format.MessageToString(self.problem))

  def Implies(self, name, cond, implicand, nodup=False):
    """Add the implication: cond ==> implicand."""
    if implicand is False:
      self.Equals(name, cond, implicand)
    elif implicand is True:
      pass
    elif isinstance(cond, Disjunction):
      for expr in cond.exprs:
        self.Implies(name, expr, implicand)
    else:
      # Ignore duplicate constraints
      if not nodup:
        ident = (self.Implies, cond, implicand)
        if ident in self.constraints:
          return
        self.constraints.add(ident)

      constraint = self.problem.constraints.add()
      constraint.name = name
      conds = cond.exprs if isinstance(cond, Conjunction) else [cond]

      if isinstance(implicand, (Disjunction, Conjunction)):
        implicands = implicand.exprs
      else:
        implicands = [implicand]

      if isinstance(implicand, Disjunction):
        n_implicands_required = 1
      else:
        n_implicands_required = len(implicands)

      for v in conds:
        constraint.literals.append(-self._GetVariableIDOrLift(v))
        # The coeff here matches the number of implicands that must be
        # true. This allows any condition being false to make the overall
        # constraint to be true.
        constraint.coefficients.append(n_implicands_required)
      for v in implicands:
        constraint.literals.append(self._GetVariableIDOrLift(v))
        constraint.coefficients.append(1)
      constraint.lower_bound = n_implicands_required

  def Equals(self, name, left, right):
    if isinstance(left, bool):
      if isinstance(right, bool):
        raise ValueError("Booleans cannot be constrained equal to each other")
      self.Equals(name, right, left)
    elif isinstance(right, bool):
      self.Assign(name, left, right)
    else:
      self.Implies(name, left, right)
      self.Implies(name, right, left)

  def Assign(self, name, left, value):
    """Assign left to the boolean value."""
    if isinstance(left, (Conjunction, Disjunction)):
      lefts = left.exprs
    else:
      lefts = [left]

    # Ignore duplicate constraints
    ident = (self.Assign, left, value)
    if ident in self.constraints:
      return
    self.constraints.add(ident)

    constraint = self.problem.constraints.add()
    constraint.name = name
    # The polarity is set to negated literals (-1) if left is a conjunction
    polarity = -1 if isinstance(left, Conjunction) else 1
    for v in lefts:
      constraint.literals.append(polarity * self._GetVariableID(v))
      constraint.coefficients.append(1)
    if (value and not isinstance(left, Conjunction) or
        not value and isinstance(left, Conjunction)):
      constraint.lower_bound = 1
    else:
      constraint.upper_bound = 0

  def BetweenNM(self, name, variables, n, m):
    """Require that the number of true variables is between n and m."""
    # Ignore duplicate constraints
    ident = (self.BetweenNM, tuple(variables), n, m)
    if ident in self.constraints:
      return
    self.constraints.add(ident)

    constraint = self.problem.constraints.add()
    constraint.name = name
    for v in variables:
      constraint.literals.append(self._GetVariableID(v))
      constraint.coefficients.append(1)
    if n is not None:
      constraint.lower_bound = n
    if m is not None:
      constraint.upper_bound = m

  def Prefer(self, var, value):
    assert isinstance(value, bool)
    obj = self.problem.objective
    # negate the ID to get a negated literal if we prefer the variable to be
    # false. Note the coefficient -1 because the objective will be minimized.
    obj.literals.append((1 if value else -1) * self._GetVariableID(var))
    obj.coefficients.append(-1)

  def _GetVariableIDOrLift(self, expr):
    if not isinstance(expr, (Disjunction, Conjunction, bool)):
      return self._GetVariableID(expr)
    else:
      tmp = self._GetTmpVariableID()
      self.Equals("Lift: {}".format(expr), tmp, expr)
      return self._GetVariableID(tmp)

  def _GetTmpVariableID(self):
    name = "tmp{}".format(self._next_id)
    self._GetVariableID(name)
    return name

  def _GetVariableID(self, var):
    assert not isinstance(var, (Disjunction, Conjunction, bool)), var
    i = self._id_table.get(var)
    if i:
      return i
    else:
      i = self._next_id
      assert i == len(self._variables) + 1
      assert len(self._id_table) == len(self._variables)
      self._next_id += 1
      self._id_table[var] = i
      self._variables.append(var)
      return i

  def Hint(self, var, value):
    """Hint the solver than var should have value."""
    # TODO(ampere): Add support for hinting the SAT solver with variable values.
