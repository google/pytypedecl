"""Input a file and output inferred types.
"""

from pytypedecl import optimize
from pytypedecl.match import sat_encoder
from pytypedecl.parse import parser
from pytypedecl.parse import utils as parse_utils
from pytypedecl.parse import visitors


FLAGS = flags.FLAGS  # TODO: move to google/


class TypeInferencer(object):
  """Encapsulates a parser, builtins, and solver."""

  # TODO: This is a very *partial* implementation, and currently
  #                  only handles classes

  def __init__(self, builtins=None):
    self.encoder = sat_encoder.SATEncoder()
    self.parser = parser.TypeDeclParser(parser.DEFAULT_VERSION)
    builtins = builtins or parse_utils.GetBuiltins()
    builtins = builtins.Visit(optimize.ExpandSignatures())
    self.builtins = visitors.LookupClasses(builtins)

  def ParseAndSolve(self, src):
    parsed = self.ParseAndLookup(src)
    return self.Solve(parsed)

  def Solve(self, parsed):
    class_names = [c.name for c in parsed.classes]
    # If all classes don't have unique names, the returned result could be
    # missing a result
    assert len(set(class_names)) == len(class_names), class_names

    res = self.SolveFromParsedLookedUpClasses(parsed.classes)
    res_by_name = {k.name: v for k, v in res.items()}
    assert len(res) == len(res_by_name)
    if res_by_name:  # Solver() can return empty dict if unsatisfiable
      assert set(class_names).issubset(set(res_by_name)), (
          class_names, res_by_name.keys())
    return res_by_name

  def SolveFromParsedLookedUpClasses(self, parsed_classes):
    """Input from LookupParsed(...), output is a solution."""
    self.encoder.Generate(self.builtins.classes, parsed_classes)
    return self.encoder.Solve()

  def ParseAndLookup(self, src):
    parsed = self.parser.Parse(src)
    return self.LookupParsed(parsed)

  def LookupParsed(self, parsed):
    # This method is split out for unit testing.
    parsed = parsed.Visit(optimize.ExpandSignatures())
    # Change pytd.NamedType to pytd.ClassType(cls=None):
    return visitors.LookupClasses(parsed)


def main(unused_argv):
  raise NotImplementedError("Use sat_encoder_test for now")  # TODO


if __name__ == "__main__":
  app.run()
