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




def GetSATRunnerBinary():
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
    return not self == other

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
    return not self == other

  # __hash__(self) uses tuple.__hash__, which is "good enough"

  def __str__(self):
    return "(" + " | ".join(str(t) for t in self.exprs) + ")"


class SATProblem(object):
  """A simplified SAT solver interface.

  Allows access to an individual result by variable name, or iteration over
  (var, value) pairs.
  """

  def __init__(self, name="", initial_polarity=True):
    self.problem = boolean_problem_pb2.LinearBooleanProblem()
    self.problem.name = name
    self.initial_polarity = initial_polarity
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
            "initial_polarity={self.initial_polarity}, "
            "_next_id={self._next_id}, "
            "_variables={self._variables}, "
            "problem={self.problem!s}, "
            "constraints={self.constraints!r}, "
            "_results={self._results!r}"
            ")").format(type=type(self).__name__,
                        self=self)

  def Solve(self):
    """Solve the SAT problem that has been created by calling methods on self.

    The result is available by self[var] or iterating over self
    """

    self.Finalize()
    problemfile, solutionfile, commandline = self._BuildSolverCmd()
    solution = None
    try:
      subprocess.check_call(commandline)
      logging.info("Loading SAT problem buffer: %r", solutionfile)
      solution = boolean_problem_pb2.LinearBooleanProblem()
      if logging.getLogger().isEnabledFor(logging.DEBUG):
        logging.debug("SAT pretty/solution:\n%s\nSAT pretty (end)",
                      self.PrettyPB())
        # logging.debug("SAT pb/solution:\n%s\nSAT pb (end)", self.problem)
      with open(solutionfile, "rb") as fi:
        solution.ParseFromString(fi.read())
      self._results = {v: None for v in self._variables}
      if logging.getLogger().isEnabledFor(logging.DEBUG):
        # The following will contain the problem also:
        logging.debug("SAT result")
        logging.debug("%s", solution)
        logging.debug("%s", self.PrettyPB())
        logging.debug("SAT result (end)")
      if not solution.assignment.literals and self._variables:
        logging.error("SAT solver failed.")
        self._results = {}
        return
      for varid in solution.assignment.literals:
        self._results[self._variables[abs(varid) - 1]] = varid > 0
    except subprocess.CalledProcessError:
      logging.error("SAT solver failed. Returning the empty result.",
                    exc_info=True)
      self._results = {}
      return
    finally:
      os.unlink(problemfile)
      os.unlink(solutionfile)
      if logging.getLogger().isEnabledFor(logging.DEBUG):
        if solution and solution.HasField("assignment"):
          logging.debug(
              "solution assignment: %s",
              text_format.MessageToString(solution))
          logging.debug("solution assignment (end)")
        else:
          logging.debug(
              "solution problem: %s",
              text_format.MessageToString(self.problem))
          logging.debug("solution problem (end)")

  def Finalize(self):
    """Fill in the final details of the protobuf."""
    logging.info("%d formulae, %d variables",
                 len(self.problem.constraints), len(self._variables))
    self.problem.num_variables = self._next_id - 1
    # The var_names aren't needed but don't do any harm, except for taking up a
    # bit of space:
    self.problem.var_names.extend(str(v) for v in self._variables)
    self.ValidatePB()
    if logging.getLogger().isEnabledFor(logging.DEBUG):
      for i, var in enumerate(self._variables):
        logging.debug("%d: %r", i + 1, var)
      logging.debug("SAT pretty/problem:\n%s\nSAT pretty (end)",
                    self.PrettyPB())

  def _BuildSolverCmd(self):
    """File names and commandline list for sat_runner."""
    logging.info("Storing SAT problem buffer")
    tmpdir = os.environ.get("TEST_TMPDIR") or os.environ.get("TMPDIR")
    with tempfile.NamedTemporaryFile(
        prefix="problem_", delete=False, dir=tmpdir, mode="wb") as fi:
      fi.write(self.problem.SerializeToString())
      problemfile = fi.name

    logging.info("Solving: %r", problemfile)
    # Ensure the solutionfile exists and is empty
    with tempfile.NamedTemporaryFile(
        prefix="solution_", delete=False, dir=tmpdir) as solutionfi:
      solutionfi.write("")
      solutionfile = solutionfi.name
    commandline = [GetSATRunnerBinary()]
    # commandline += ["-strict_validity"]  # TODO: restore
    if logging.getLogger().isEnabledFor(logging.INFO):
      commandline += ["-logtostderr"]
    if self.initial_polarity:
      commandline += ["-params", "initial_polarity:0"]
    commandline += [
        "-input=" + problemfile,
        "-output=" + solutionfile,
        "-use_lp_proto=false"]
    logging.debug("solver cmd: %s", commandline)
    return problemfile, solutionfile, commandline

  def Implies(self, cond, implicand, descr_so_far=None):
    """Add implication: cond ==> implicand."""
    descr = (descr_so_far or []) + ["{} ==> {}".format(cond, implicand)]
    if implicand is False:
      self.Equals(cond, implicand, descr)
    elif implicand is True:
      return
    elif isinstance(cond, Disjunction):
      for expr in cond.exprs:
        self.Implies(expr, implicand, descr)
    # TODO: should we add the following simplification?
    #                  it's probably not general enough; but it catches
    #                  some cases of duplication
    # elif isinstance(implicand, Conjunction) and cond in implicand.exprs:
    #   new_implicand_exprs = [x for x in implicand.exprs if x != cond]
    #   self.Implies(cond, Conjunction(new_implicand_exprs), descr)
    #   return
    else:
      # Ignore duplicate constraints
      ident = ("Implies", cond, implicand)
      if ident in self.constraints:
        return
      self.constraints.add(ident)

      constraint = self._AddProblemConstraint(descr)
      conds = cond.exprs if isinstance(cond, Conjunction) else [cond]
      implicands = (
          implicand.exprs if isinstance(implicand, (Disjunction, Conjunction))
          else [implicand])
      n_implicands_required = (
          1 if isinstance(implicand, Disjunction) else len(implicands))

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

  def Equals(self, left, right, descr_so_far=None):
    """Add equality: left <==> right."""
    descr = (descr_so_far or []) + ["{} <==> {}".format(left, right)]
    if isinstance(left, bool):
      if isinstance(right, bool):
        raise ValueError("Booleans cannot be constrained equal to each other")
      self.Equals(right, left, descr)
    elif isinstance(right, bool):
      self.Assign(left, right, descr)
    else:
      self.Implies(left, right, descr)
      self.Implies(right, left, descr)

  def Assign(self, left, value, descr_so_far=None):
    """Add assignment of left to the boolean value."""  # TODO(pludeman): assign left to right????
    descr = (descr_so_far or []) + ["{} :=> {}".format(left, value)]
    if isinstance(left, (Conjunction, Disjunction)):
      lefts = left.exprs
    else:
      lefts = [left]

    # Ignore duplicate constraints
    ident = ("Assign", left, value)
    if ident in self.constraints:
      return
    self.constraints.add(ident)

    constraint = self._AddProblemConstraint(descr)
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

  def BetweenNM(self, variables, n, m, ty, descr_so_far=None):
    """Add requirement that the number of true variables is between n and m."""
    descr = (descr_so_far or []) + ["Force assign {}".format(ty)]
    # Ignore duplicate constraints
    ident = ("BetweenNM", tuple(variables), n, m)
    if ident in self.constraints:
      return
    self.constraints.add(ident)

    constraint = self._AddProblemConstraint(descr)
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
    if isinstance(expr, (Disjunction, Conjunction, bool)):
      tmp = self._GetTmpVariableID()
      self.Equals(tmp, expr, ["Lift: {}".format(expr)])
      return self._GetVariableID(tmp)
    else:
      # It's not necessarily a string ... e.g. sat_encoder.Equality
      # TODO: document the possible expr types
      return self._GetVariableID(expr)

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

  def _AddProblemConstraint(self, descr):
    constraint = self.problem.constraints.add()
    constraint.name = " ... ".join(descr)
    return constraint

  def Hint(self, var, value):
    """Hint the solver than var should have value."""
    # TODO(ampere): Add support for hinting the SAT solver with variable values.
    pass

  def ValidatePB(self):
    for constraint in self.problem.constraints:
      assert len(constraint.literals) == len(constraint.coefficients)
      assert all(lit != 0 for lit in constraint.literals)
      assert all(coef != 0 for coef in constraint.coefficients)
      duplicates = [
          lit for lit, count in collections.Counter(
              abs(lit) for lit in constraint.literals).items()
          if count > 1]
      # assert not duplicates, ([(self.problem.var_names[abs(lit)-1], lit) for lit in duplicates], str(constraint))  # TODO: fix

  def PrettyPB(self):
    """Pretty version of the protobuff."""
    return "".join(self._PrettyPBYield())

  def _PrettyPBYield(self):
    p = self.problem
    yield "name: '{}'\n".format(p.name)
    yield "num_variables: {:d}\n".format(p.num_variables)
    yield "var_names: {}\n".format(
        [(i, str(n)) for i, n in enumerate(p.var_names)])
    for constraint in p.constraints:
      # TODO: this is a duplicate of ValidatePB
      duplicates = [p.var_names[abs(lit)-1]
                    for lit, count in collections.Counter(
                        abs(lit) for lit in constraint.literals).items()
                    if count > 1]
      if duplicates:
        yield "***duplicates: {} ".format(duplicates)
      if constraint.HasField("lower_bound"):
        yield "{:d} <= ".format(constraint.lower_bound)
      for coef, lit in zip(constraint.coefficients, constraint.literals):
        if lit < 0:
          lit_sign = "-"
          lit = -lit
        else:
          lit_sign = ""
        try:
          lit_name = p.var_names[lit-1]  # The protobuf uses 1-origin indexing
        except IndexError:
          lit_name = "(!!{:d}!!)".format(lit)
        yield "{:d}*{}{} ".format(coef, lit_sign, lit_name)
      if constraint.HasField("upper_bound"):
        yield "<= {:d} ".format(constraint.upper_bound)
      yield " # {}\n".format(constraint.name)
