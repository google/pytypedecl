"""Tests for match.sat_problem."""

import unittest
from pytypedecl.match import sat_problem


class SatProblemTest(unittest.TestCase):

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

  def testEquals(self):
    problem = sat_problem.SATProblem(name="PROBLEM")
    problem.Equals("foo == bar", "foo", "bar")
    self.assertItemsEqual(["foo", "bar"], problem._variables)
    problem.Solve()
    # TODO: Can we improve str(problem) for debugging and give that
    #                  as the 3rd param to assertXXX? Right now, str(problem)
    #                  is really ugly.
    # TODO: Solver() has two possible results. We could add an
    #                  additional constraint like foo=True to reduce to a single
    #                  possibility, allowing us to use self.assertItemsEqual
    self.assertTrue(dict(foo=True, bar=True) == problem._results or
                    dict(foo=False, bar=False) == problem._results)

  # TODO: The following is somewhat like a "change detector"
  #                  test. THIS TEST IS FRAGILE but not flaky and should be
  #                  modified to be more robust.
  #                  However, it's also useful to check that the expected
  #                  constraints were generated from the original problem.
  #                  The main problem is that it's overly prescriptive, but
  #                  it's a fair bit of work to make a PB comparitor that's
  #                  more forgiving of small changes.
  def testEqualsPB(self):
    problem = sat_problem.SATProblem(name="PROBLEM")
    problem.Equals("foo == bar", "foo", "bar")
    problem_expected = _make_problem_pb("""
      name: "PROBLEM"
      constraints {
        literals: -1        literals: 2
        coefficients: 1     coefficients: 1
        lower_bound: 1
        name: "foo == bar"
      }
      constraints {
        literals: -2        literals: 1
        coefficients: 1     coefficients: 1
        lower_bound: 1
        name: "foo == bar"
      }""")
    self.assertEqual(str(problem_expected), str(problem.problem))


def _make_problem_pb(ascii):
  """Create LinearBooleanProblem protobuf from ascii representation."""
  result = boolean_problem_pb2.LinearBooleanProblem()
  text_format.Parse(ascii, result)
  return result


if __name__ == "__main__":
  unittest.main()
