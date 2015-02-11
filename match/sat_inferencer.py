"""Input a file and output inferred types.
"""

import logging
from pytype import typegraphvm
from pytypedecl import optimize
from pytypedecl import pytd
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
    self.builtins.Visit(visitors.VerifyLookup())  # TODO: remove

  def ParseAndSolve(self, src):
    parsed = self.parser.Parse(src)
    parsed = self.LookupParsed(parsed)
    return self.Solve(parsed)

  def LookupParsed(self, parsed):
    # This method is split out for unit testing.
    parsed = parsed.Visit(optimize.ExpandSignatures())
    # Change pytd.NamedType to pytd.ClassType(cls=None):
    res = visitors.LookupClasses(parsed, global_module=self.builtins)
    res.Visit(visitors.VerifyLookup())  # TODO: remove
    return res

  def Solve(self, parsed):
    class_names = [c.name for c in parsed.classes]
    # If all classes don't have unique names, the returned result could be
    # missing a result
    assert len(set(class_names)) == len(class_names), class_names

    self.encoder.Generate(self.builtins.classes, parsed.classes)
    res = self.encoder.Solve()
    res_by_name = {k.name: v for k, v in res.items()}
    assert len(res) == len(res_by_name)
    if res_by_name:  # Solver() can return empty dict if unsatisfiable
      assert set(class_names).issubset(set(res_by_name)), (
          class_names, res_by_name.keys())
    return res_by_name

  def InferTypesAndSolve(self, program, debug=True, svg_output=None,
                         deep=False, expensive=True, pseudocode_output=False):
    """Run CFG type inferencer and then solver."""
    ty = typegraphvm.infer_types(program,
                                 debug=debug,
                                 deep=deep,
                                 expensive=expensive,
                                 svg_output=svg_output,
                                 pseudocode_output=pseudocode_output)

    logging.info("===Incomplete classes and functions===\n%s\n"
                 "===Incomplete classes and functions=== (end)",
                 pytd.Print(ty))

    ty = self.LookupParsed(ty)
    solve_result = self.Solve(ty)
    logging.info("===Incomplete classes and functions (2)===\n%s\n"
                 "===Incomplete classes and functions (2)=== (end)",
                 pytd.Print(ty))
    logging.info("===solve_result===\n%s\n", solve_result)

    ty = ty.Visit(visitors.ReplaceTypes(solve_result))
    logging.info("===Substituted classes and functions===\n%s\n"
                 "===Substituted classes and functions=== (end)",
                 pytd.Print(ty))

    # Delete all classes that we've resolved to another class
    # and put into a canonical order.
    # TODO: add constants, modules
    # TODO: need to distinguish between `unknown` and user-defined
    #                  and only remove `unknown`
    # TODO: in following: is this better: ?
    #                       ty.Lookup(name) for name in solve_result
    ty = ty.Replace(
        classes=tuple(sorted(
            c for c in ty.classes if c.name not in solve_result)),
        functions=tuple(sorted(ty.functions)))
    # remove duplicates, etc.:
    ty = optimize.Optimize(ty)
    # TODO: RemoveDuplicates ought to have been done by Optimize:
    ty = ty.Visit(optimize.RemoveDuplicates())

    return ty


def main(unused_argv):
  raise NotImplementedError("Use sat_encoder_test for now")  # TODO


if __name__ == "__main__":
  app.run()
