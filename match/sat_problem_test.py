"""Tests for match.sat_problem."""

import logging
from pytypedecl.match import sat_problem


FLAGS = flags.FLAGS  # TODO: move to google/


class SATProblemTest(unittest.TestCase):

  def setUp(self):
    if FLAGS.verbosity:
      logging.basicConfig(level=logging.INFO)
    self.problem = sat_problem.SATProblem(name="PROBLEM")

  def _ProblemSolveAndCheck(self, **expected):
    self.problem.Solve()
    self.assertEqual(dict(**expected), self.problem._results,
                     "Wrong result: " + str(self.problem))

  def testConjunction(self):
    self.assertEqual(True,
                     sat_problem.Conjunction([True]))
    self.assertEqual("foo",
                     sat_problem.Conjunction([True, "foo", True]))
    self.assertEqual(False,
                     sat_problem.Conjunction([True, False, True]))
    self.assertEqual(False,
                     sat_problem.Conjunction(["foo", "bar", False]))
    self.assertItemsEqual(
        ["foo", "bar"],
        sat_problem.Conjunction(["bar", "foo", True]).exprs)
    self.assertItemsEqual(
        ["foo", "bar", "zot"],
        sat_problem.Conjunction(
            ["bar", True, "foo", True,
             sat_problem.Conjunction(["zot"]),
             sat_problem.Conjunction(["zot", "zot"]),
             sat_problem.Conjunction([True, "zot", True])]).exprs)

  def testDisjunction(self):
    self.assertEqual(True,
                     sat_problem.Disjunction([True]))
    self.assertEqual(True,
                     sat_problem.Disjunction([True, "foo", True]))
    self.assertEqual(True,
                     sat_problem.Disjunction([True, False, True]))
    self.assertEqual("foo",
                     sat_problem.Disjunction(["foo", False]))
    self.assertItemsEqual(
        ["foo", "bar"],
        sat_problem.Disjunction(["bar", "foo", False]).exprs)
    self.assertItemsEqual(
        ["foo", "bar", "zot"],
        sat_problem.Disjunction(
            ["bar", False, "foo", False,
             sat_problem.Disjunction(["zot"]),
             sat_problem.Disjunction(["zot", "zot"]),
             sat_problem.Disjunction([False, "zot", False])]).exprs)

  # TODO: Add one test for each transformation in sat_problem.

  def testImplies1(self):
    self.problem.Implies("p", "q")
    self.problem.Equals("p", True)
    self.problem.Equals("q", True)
    self._ProblemSolveAndCheck(p=True, q=True)

  def testImplies2(self):
    self.problem.Implies("p", "q")
    self.problem.Equals("p", True)
    self.problem.Equals("q", False)
    self._ProblemSolveAndCheck()

  def testImplies3(self):
    self.problem.Implies("p", "q")
    self.problem.Equals("p", False)
    self.problem.Equals("q", True)
    self._ProblemSolveAndCheck(p=False, q=True)

  def testImplies4(self):
    self.problem.Implies("p", "q")
    self.problem.Equals("p", False)
    self.problem.Equals("q", False)
    self._ProblemSolveAndCheck(p=False, q=False)

  def testEquals1a(self):
    self.problem.Equals("p", "q")
    self.problem.Equals("p", True)
    self.problem.Equals("q", True)
    self._ProblemSolveAndCheck(p=True, q=True)

  def testEquals1b(self):
    self.problem.Equals("p", "q")
    self.problem.Equals("p", True)
    self.problem.Equals("q", False)
    self._ProblemSolveAndCheck()

  def testEquals1c(self):
    self.problem.Equals("p", "q")
    self.problem.Equals("p", False)
    self.problem.Equals("q", True)
    self._ProblemSolveAndCheck()

  def testEquals1d(self):
    self.problem.Equals("p", "q")
    self.problem.Equals("p", False)
    self.problem.Equals("q", False)
    self._ProblemSolveAndCheck(p=False, q=False)


class SATProblemPBTest(unittest.TestCase):

  def setUp(self):
    if FLAGS.verbosity:
      logging.basicConfig(level=logging.INFO)
    self.problem = sat_problem.SATProblem(name="PROBLEM")

  def _CheckProblemPB(self, vars_expected, ascii_expected):
    """Create LinearBooleanProblem protobuf from ascii representation."""
    self.problem.End()
    problem_expected = boolean_problem_pb2.LinearBooleanProblem()
    text_format.Parse(ascii_expected, problem_expected)
    self.assertEqual(vars_expected, self.problem._variables)
    self.assertEqual(str(problem_expected), str(self.problem.problem))

  # TODO: The following tests are somewhat like a "change detector"
  #                  test. THESE TESTS ARE FRAGILE but not flaky and should be
  #                  modified to be more robust.
  #                  However, it's also useful to check that the expected
  #                  constraints were generated from the original problem.
  #                  The main problem is that it's overly prescriptive, but
  #                  it's a fair bit of work to make a PB comparitor that's
  #                  more forgiving of small changes.

  def testImpliesPB1(self):
    self.problem.Implies("foo", True)
    self._CheckProblemPB(
        [],
        """name: "PROBLEM"
        num_variables: 0
        """)

  def testImpliesPB2(self):
    self.problem.Implies("foo", False)
    self._CheckProblemPB(
        ["foo"],
        """name: "PROBLEM"
        num_variables: 1  var_names: "foo"
        constraints {
          literals: 1
          coefficients: 1
          upper_bound: 0
          name: "foo ==> False ... foo <==> False ... foo :=> False"
        }""")

  def testImpliesPB3(self):
    self.problem.Implies("foo", "bar")
    self._CheckProblemPB(
        ["foo", "bar"],
        """name: "PROBLEM"
        num_variables: 2  var_names: "foo"  var_names: "bar"
        constraints {
          literals: -1      literals: 2
          coefficients: 1   coefficients: 1
          lower_bound: 1
          name: "foo ==> bar"
        }""")

  def testEqualsPB1(self):
    self.problem.Equals("foo", "bar")
    self._CheckProblemPB(
        ["foo", "bar"],
        """name: "PROBLEM"
        num_variables: 2  var_names: "foo" var_names: "bar"
        constraints {
          literals: -1        literals: 2
          coefficients: 1     coefficients: 1
          lower_bound: 1
          name: "foo <==> bar ... foo ==> bar"
        }
        constraints {
          literals: -2        literals: 1
          coefficients: 1     coefficients: 1
          lower_bound: 1
          name: "foo <==> bar ... bar ==> foo"
        }""")

  def testEqualsPB2(self):
    self.problem.Equals("foo", True)
    self._CheckProblemPB(
        ["foo"],
        """name: "PROBLEM"
        num_variables: 1  var_names: "foo"
        constraints {
          literals: 1
          coefficients: 1
          lower_bound: 1
          name: "foo <==> True ... foo :=> True"
        }""")

  def testEqualsPB3(self):
    self.problem.Equals(True, "foo")
    self._CheckProblemPB(
        ["foo"],
        """name: "PROBLEM"
        num_variables: 1  var_names: "foo"
        constraints {
          literals: 1
          coefficients: 1
          lower_bound: 1
          name: "True <==> foo ... foo <==> True ... foo :=> True"
        }""")

  def testEqualsPB4(self):
    self.problem.Equals("foo", False)
    self._CheckProblemPB(
        ["foo"],
        """name: "PROBLEM"
        num_variables: 1  var_names: "foo"
        constraints {
          literals: 1
          coefficients: 1
          upper_bound: 0
          name: "foo <==> False ... foo :=> False"
        }""")

  def testEqualsPB5(self):
    self.problem.Equals(False, "foo")
    self._CheckProblemPB(
        ["foo"],
        """name: "PROBLEM"
        num_variables: 1  var_names: "foo"
        constraints {
          literals: 1
          coefficients: 1
          upper_bound: 0
          name: "False <==> foo ... foo <==> False ... foo :=> False"
        }""")

  def testAssignPB1(self):
    self.problem.Assign("foo", "bar")
    self._CheckProblemPB(
        # TODO: why isn't this ["foo", "bar"] and below?
        ["foo"],
        """name: "PROBLEM"
        num_variables: 1  var_names: "foo"
        constraints {
          literals: 1
          coefficients: 1
          lower_bound: 1
          name: "foo :=> bar"
        }""")

  def testAssignPB2(self):
    self.problem.Assign("foo", False)
    self._CheckProblemPB(
        ["foo"],
        """name: "PROBLEM"
        num_variables: 1  var_names: "foo"
        constraints {
          literals: 1
          coefficients: 1
          upper_bound: 0
          name: "foo :=> False"
        }""")

  def testAssignPB3(self):
    self.problem.Assign("foo", True)
    self._CheckProblemPB(
        ["foo"],
        """name: "PROBLEM"
        num_variables: 1  var_names: "foo"
        constraints {
          literals: 1
          coefficients: 1
          lower_bound: 1
          name: "foo :=> True"
        }""")


if __name__ == "__main__":
  unittest.main()
