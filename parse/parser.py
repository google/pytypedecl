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


"""Parser & Lexer for type declaration language."""

# TODO: look at https://github.com/JetBrains/python-skeletons
#                  for an alternative syntax (e.g. T <= Foo for T such
#                  that it's Foo or subclass) ... doesn't have interfaces
#                  or intersection

# pylint: disable=g-bad-name, g-short-docstring-punctuation
# pylint: disable=g-doc-args, g-no-space-after-docstring-summary
# pylint: disable=g-space-before-docstring-summary
# pylint: disable=g-backslash-continuation
# pylint: disable=line-too-long

from ply import lex
from ply import yacc
from pytypedecl import optimize
from pytypedecl import pytd
from pytypedecl import optimize


class PyLexer(object):
  """Lexer for type declaration language."""

  def __init__(self):
    # TODO: See comments with PyParser about generating the
    #                  $GENFILESDIR/pytypedecl_lexer.py and using it by
    #                  calling lex.lex(lextab=pytypedecl_lexer)
    self.lexer = lex.lex(module=self, debug=False)
    self.lexer.escaping = False

  def set_parse_info(self, data, filename):
    self.data = data
    self.filename = filename

  # The ply parsing library expects class members to be named in a specific way.
  t_ARROW = r'->'
  t_AT = r'@'
  t_COLON = r':'
  t_COMMA = r','
  t_DOT = r'\.'
  t_LBRACKET = r'\<'
  t_LPAREN = r'\('
  t_MINUS = r'-'
  t_PLUS = r'\+'
  t_RBRACKET = r'\>'
  t_RPAREN = r'\)'

  reserved = [
      'class',
      'def',
      'pass',
      'raises',
      'extends',
      'and',
      'or',
  ]

  # Define keyword tokens, so parser knows about them.
  # We generate them in t_NAME.
  locals().update({'t_' + id.upper(): id for id in reserved})

  tokens = [
      'ARROW',
      'AT',
      'COLON',
      'COMMA',
      # 'COMMENT',  # Not used in the grammar; only used to discard comments
      'DOT',
      'LBRACKET',
      'LPAREN',
      'MINUS',
      'NAME',
      'NUMBER',
      'PLUS',
      'RBRACKET',
      'RPAREN',
      'STRING',
  ] + [id.upper() for id in reserved]

  # Ignored characters
  t_ignore = ' \t'

  def t_NAME(self, t):
    (r"""([a-zA-Z_][a-zA-Z0-9_\.]*)|"""
     r"""(`[^`]*`)""")
    if t.value[0] == r'`':
      # Permit token names to be enclosed by backticks (``), to allow for names
      # that are keywords in pytd syntax.
      assert t.value[-1] == r'`'
      t.value = t.value[1:-1]
      t.type = 'NAME'
    elif t.value in self.reserved:
      t.type = t.value.upper()
    return t

  def t_STRING(self, t):
    (r"""'([^']|\\')*'|"""
     r'"([^"]|\\")*"')
    # TODO: full Python string syntax (e.g., """...""", r"...")
    # TODO: use something like devtools/python/library_types/ast.py _ParseLiteral
    t.value = eval(t.value)
    return t

  def t_NUMBER(self, t):
    r"""[-+]?[0-9]+(\.[0-9]*)?"""
    # TODO: full Python number syntax
    # TODO: move +/- to grammar?
    t.value = float(t.value) if '.' in t.value else int(t.value)
    return t

  def t_COMMENT(self, t):
    r"""\#.*"""  # implicit end of line
    # No return value. Token discarded

  def t_newline(self, t):
    r"""\n+"""  # TODO: is this correct?
    t.lexer.lineno += t.value.count('\n')
    t.lexer.on_newline = True

  def t_error(self, t):
    raise make_syntax_error(self, "Illegal character '%s'" % t.value[0], t)


class PyParser(object):
  """Parser for type declaration language."""

  # TODO: Check for name clashes.

  def __init__(self, **kwargs):
    # TODO: Don't generate the lex/yacc tables each time. This should
    #                  be done by a separate program that imports this module
    #                  and calls yacc.yacc(write_tables=True,
    #                  outputdir=$GENFILESDIR, tabmodule='pytypedecl_parser')
    #                  and similar params for lex.lex(...).  Then:
    #                    import pytypdecl_parser
    #                    self.parser = yacc.yacc(tabmodule=pytypedecl_parser)
    #                  [might also need optimize=True]
    self.lexer = PyLexer()
    self.tokens = self.lexer.tokens
    self.parser = yacc.yacc(
        start='defs',
        module=self,
        debug=False,
        # debuglog=yacc.PlyLogger(sys.stderr),
        # errorlog=yacc.NullLogger(),  # If you really want to suppress messages
        **kwargs)

  def Parse(self, data, filename=None, **kwargs):
    self.data = data  # Keep a copy of what's being parsed
    self.filename = filename if filename else '<string>'
    self.lexer.set_parse_info(self.data, self.filename)
    return self.parser.parse(data, **kwargs)

  precedence = (
      ('left', 'OR'),
      ('left', 'AND'),
      ('left', 'COMMA'),
  )

  def p_defs(self, p):
    """defs : funcdefs classes
    """
    # TODO: change the definition of defs to:
    #            defs : defs def | defs
    #            def : funcdef | classdef
    #        This will require handling indent/exdent and/or allowing {...}.
    #        Also requires supporting INDENT/DEDENT because otherwise it's
    #        ambiguous on the meaning of a funcdef after a classdef
    funcdefs = [x for x in p[1] if isinstance(x, optimize.NameAndSignature)]
    constants = [x for x in p[1] if isinstance(x, pytd.Constant)]
    if (set(f.name for f in funcdefs) | set(c.name for c in constants) !=
        set(d.name for d in p[1])):
      # TODO: raise a syntax error right when the identifier is defined.
      raise make_syntax_error(self, 'Duplicate identifier(s)', p)
    p[0] = pytd.TypeDeclUnit(constants=constants,
                             functions=optimize.MergeSignatures(funcdefs),
                             classes=p[2]).ExpandTemplates([])

  def p_classes(self, p):
    """classes : classes classdef"""
    p[0] = p[1] + [p[2]]

  def p_classes_null(self, p):
    """classes :"""
    p[0] = []

  # TODO(raoulDoc): doesn't support nested classes
  # TODO: parents is redundant -- should match what's in .py file
  def p_classdef(self, p):
    """classdef : CLASS template NAME parents COLON class_funcs"""
    #             1     2        3    4       5     6
    # TODO: do name lookups for template within class_funcs
    funcdefs = [x for x in p[6] if isinstance(x, optimize.NameAndSignature)]
    constants = [x for x in p[6] if isinstance(x, pytd.Constant)]
    if (set(f.name for f in funcdefs) | set(c.name for c in constants) !=
        set(d.name for d in p[6])):
      # TODO: raise a syntax error right when the identifier is defined.
      raise make_syntax_error(self, 'Duplicate identifier(s)', p)
    p[0] = pytd.Class(name=p[3], parents=p[4],
                      methods=optimize.MergeSignatures(funcdefs),
                      constants=constants, template=p[2])

  def p_class_funcs(self, p):
    """class_funcs : funcdefs"""
    p[0] = p[1]

  def p_class_funcs_pass(self, p):
    """class_funcs : PASS"""
    p[0] = []

  def p_parents(self, p):
    """parents : LPAREN parent_list RPAREN"""
    p[0] = p[2]

  def p_parents_null(self, p):
    """parents :"""
    p[0] = []

  def p_parent_list_multi(self, p):
    """parent_list : parent_list COMMA NAME"""
    p[0] = p[1] + [p[3]]

  def p_parent_list_1(self, p):
    """parent_list : NAME"""
    p[0] = [p[1]]

  def p_template(self, p):
    """template : LBRACKET templates RBRACKET"""
    p[0] = p[2]

  def p_template_null(self, p):
    """template : """
    # TODO: test cases
    p[0] = []

  def p_templates_multi(self, p):
    """templates : templates COMMA template_item"""
    p[0] = p[1] + [p[3]]

  def p_templates_1(self, p):
    """templates : template_item"""
    p[0] = [p[1]]

  def p_template_item(self, p):
    """template_item : NAME"""
    p[0] = pytd.TemplateItem(p[1], pytd.BasicType('object'), 0)

  def p_template_item_subclss(self, p):
    """template_item : NAME EXTENDS compound_type"""
    p[0] = pytd.TemplateItem(p[1], p[3], 0)

  def p_funcdefs_func(self, p):
    """funcdefs : funcdefs funcdef"""
    p[0] = p[1] + [p[2]]

  def p_funcdefs_constant(self, p):
    """funcdefs : funcdefs constantdef"""
    p[0] = p[1] + [p[2]]

  # TODO(raoulDoc): doesn't support nested functions
  def p_funcdefs_null(self, p):
    """funcdefs :"""
    p[0] = []

  def p_constantdef(self, p):
    """constantdef : NAME COLON compound_type"""
    p[0] = pytd.Constant(p[1], p[2])

  def p_funcdef(self, p):
    """funcdef : provenance DEF template NAME LPAREN params RPAREN return raises signature"""
    #            1          2   3        4     5     6      7      8      9     10
    # TODO: do name lookups for template within params, return, raises
    signature = pytd.Signature(params=p[6], return_type=p[8], exceptions=p[9],
                               template=p[3], provenance=p[1])
    p[0] = optimize.NameAndSignature(name=p[4], signature=signature)

  def p_return(self, p):
    """return : ARROW compound_type"""
    p[0] = p[2]

  def p_return_null(self, p):
    """return :"""
    p[0] = pytd.BasicType('None')

  def p_params_multi(self, p):
    """params : params COMMA param"""
    p[0] = p[1] + [p[3]]

  def p_params_1(self, p):
    """params : param"""
    p[0] = [p[1]]

  def p_params_null(self, p):
    """params :"""
    p[0] = []

  def p_param(self, p):
    """param : NAME"""
    # type is optional and defaults to "object"
    p[0] = pytd.Parameter(p[1], pytd.BasicType("object"))

  def p_param_and_type(self, p):
    """param : NAME COLON compound_type"""
    p[0] = pytd.Parameter(p[1], p[3])

  def p_raise(self, p):
    """raises : RAISES exceptions"""
    p[0] = p[2]

  def p_raise_null(self, p):
    """raises :"""
    p[0] = []

  def p_exceptions_1(self, p):
    """exceptions : exception"""
    p[0] = [p[1]]

  def p_exceptions_multi(self, p):
    """exceptions : exceptions COMMA exception"""
    p[0] = p[1] + [p[3]]

  def p_exception(self, p):
    """exception : compound_type"""
    p[0] = pytd.ExceptionDef(p[1])

  def p_identifier_name(self, p):
    """identifier : NAME"""
    p[0] = pytd.BasicType(p[1])

  def p_identifier_string(self, p):
    """identifier : STRING"""
    p[0] = pytd.Scalar(p[1])

  def p_identifier_number(self, p):
    """identifier : NUMBER"""
    p[0] = pytd.Scalar(p[1])

  def p_compound_type_and(self, p):
    """compound_type : compound_type AND compound_type"""
    # This rule depends on precedence specification
    if (isinstance(p[1], pytd.IntersectionType) and
        isinstance(p[3], pytd.BasicType)):
      p[0] = pytd.IntersectionType(p[1].type_list + [p[3]])
    elif (isinstance(p[1], pytd.BasicType) and
          isinstance(p[3], pytd.IntersectionType)):
      # associative
      p[0] = pytd.IntersectionType([p[1]] + p[3].type_list)
    else:
      p[0] = pytd.IntersectionType([p[1], p[3]])

  def p_compound_type_or(self, p):
    """compound_type : compound_type OR compound_type"""
    # This rule depends on precedence specification
    if (isinstance(p[1], pytd.UnionType) and
        isinstance(p[3], pytd.BasicType)):
      p[0] = pytd.UnionType(p[1].type_list + [p[3]])
    elif (isinstance(p[1], pytd.BasicType) and
          isinstance(p[3], pytd.UnionType)):
      # associative
      p[0] = pytd.UnionType([p[1]] + p[3].type_list)
    else:
      p[0] = pytd.UnionType([p[1], p[3]])

  # This is parameterized type
  # TODO(raoulDoc): support data types in future?
  # data  Tree a  =  Leaf a | Branch (Tree a) (Tree a)
  # TODO(raoulDoc): restricted to 2 params on purpose
  # might want to extend in future if there are use cases
  # TODO(raoulDoc): should we consider nested generics?

  # TODO: for generic types, we explicitly don't allow
  #                  compound_type[...] but insist on identifier[...] ... this
  #                  is because the grammar would be ambiguous, but for some
  #                  reason PLY didn't come up with a shift/reduce conflict but
  #                  just quietly promoted OR and AND above LBRACKET
  #                  (or, at least, that's what I think happened). Probably best
  #                  to not use precedence and write everything out fully, even
  #                  if it's a more verbose grammar.

  def p_compound_type_generic_1(self, p):
    """compound_type : identifier LBRACKET compound_type RBRACKET"""
    p[0] = pytd.GenericType1(base_type=p[1], type1=p[3])

  def p_compound_type_generic_2(self, p):
    """compound_type : identifier LBRACKET compound_type COMMA compound_type RBRACKET"""
    p[0] = pytd.GenericType2(base_type=p[1], type1=p[3], type2=p[5])

  def p_compound_type_paren(self, p):
    """compound_type : LPAREN compound_type RPAREN"""
    p[0] = p[2]

  def p_compound_type_identifier(self, p):
    """compound_type : identifier"""
    p[0] = p[1]

  def p_provenance_approved(self, p):
    """provenance :"""
    p[0] = ''  # TODO: implement

  def p_provenance_inferred(self, p):
    """provenance : DOT DOT DOT"""
    p[0] = '...'  # TODO: implement

  def p_provenance_negated(self, p):
    """provenance : MINUS MINUS MINUS"""
    p[0] = '---'  # TODO: implement

  def p_provenance_locked(self, p):
    """provenance : PLUS PLUS PLUS"""
    # TODO: verify that all other rules for this definition are
    #                  either 'locked' or 'negated' (none 'inferred' or
    #                  'approved'
    p[0] = '+++'  # TODO: implement

  def p_signature_(self, p):
    """signature : AT STRING"""
    p[0] = p[2]

  def p_signature_none(self, p):
    """signature :"""
    p[0] = None

  def p_error(self, p):
    raise make_syntax_error(self, 'Parse error', p)


def make_syntax_error(parser_or_tokenizer, msg, p):
  # SyntaxError(msg, (filename, lineno, offset, line))
  # is output in a nice format by traceback.print_exception
  # TODO: add test cases for this (including beginning/end of file,
  #                  lexer error, parser error)

  # Convert the lexer's offset to an offset within the line with the error
  # TODO: use regexp to split on r'[\r\n]' (for Windows, old MacOS):
  last_line_offset = parser_or_tokenizer.data.rfind('\n', 0, p.lexpos) + 1
  line, _, _ = parser_or_tokenizer.data[last_line_offset:].partition('\n')

  raise SyntaxError(msg,
                    (parser_or_tokenizer.filename,
                     p.lineno, p.lexpos - last_line_offset + 1, line))
