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

import collections
import sys
import traceback
from ply import lex
from ply import yacc
from pytypedecl import pytd


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
    self.indent_stack = [0]
    self.open_brackets = 0

  # The ply parsing library expects class members to be named in a specific way.
  t_ARROW = r'->'
  t_AT = r'@'
  t_COLON = r':'
  t_COMMA = r','
  t_DOT = r'\.'
  t_MINUS = r'-'
  t_PLUS = r'\+'
  t_INDENT = r'(?!i)i'
  t_DEDENT = r'(?!d)d'

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
      'DEDENT',
      'DOT',
      'INDENT',
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

  def t_LBRACKET(self, t):
    r"""<"""
    self.open_brackets += 1
    return t

  def t_RBRACKET(self, t):
    r""">"""
    self.open_brackets -= 1
    return t

  def t_LPAREN(self, t):
    r"""\("""
    self.open_brackets += 1
    return t

  def t_RPAREN(self, t):
    r"""\)"""
    self.open_brackets -= 1
    return t

  def t_TAB(self, t):
    r"""\t"""
    # Since nobody can agree anymore what how wide tab characters are supposed
    # to be, disallow them altogether.
    raise make_syntax_error(self, 'Use spaces, not tabs', t)

  def t_WHITESPACE(self, t):
    r"""[\n\r ]+"""  # explicit [...] instead of \s, to omit tab
    t.lexer.lineno += t.value.count('\n')
    if self.open_brackets:
      # inside (...) and <...>, we allow any kind of whitespace and indentation.
      return
    spaces_and_newlines = t.value.replace('\r', '')
    i = spaces_and_newlines.rfind('\n')
    if i < 0:
      # whitespace in the middle of line
      return
    indent = len(spaces_and_newlines) - i - 1
    if indent < self.indent_stack[-1]:
      self.indent_stack.pop()
      if indent < self.indent_stack[-1]:
        # TODO: support multi-level dedent?
        make_syntax_error(self, 'invalid dedent', t)
      t.type = 'DEDENT'
      return t
    elif indent > self.indent_stack[-1]:
      self.indent_stack.append(indent)
      t.type = 'INDENT'
      return t
    else:
      # same indent as before, ignore.
      return None

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
    r"""\#[^\n]*"""
    # No return value. Token discarded

  def t_error(self, t):
    raise make_syntax_error(self, "Illegal character '%s'" % t.value[0], t)


Params = collections.namedtuple('Params', ['required', 'has_optional'])
NameAndSig = collections.namedtuple('NameAndSig', ['name', 'signature'])


def MergeSignatures(signatures):
  """Given a list of pytd function signature declarations, group them by name.

  Converts a list of NameAndSignature items to a list of Functions (grouping
  signatures by name).

  Arguments:
    signatures: A list of tuples (name, signature).

  Returns:
    A list of instances of pytd.Function.
  """

  name_to_signatures = collections.OrderedDict()

  for name, signature in signatures:
    if name not in name_to_signatures:
      name_to_signatures[name] = []
    name_to_signatures[name].append(signature)

  # TODO: Return this as a dictionary.
  return [pytd.Function(name, signatures)
          for name, signatures in name_to_signatures.viewitems()]


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
        start='unit',
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

  def p_unit(self, p):
    """unit : alldefs"""
    funcdefs = [x for x in p[1] if isinstance(x, NameAndSig)]
    constants = [x for x in p[1] if isinstance(x, pytd.Constant)]
    classes = [x for x in p[1] if isinstance(x, pytd.Class)]
    if ({f.name for f in funcdefs} & {o.name for o in constants} or
        {o.name for o in constants} & {c.name for c in classes} or
        {c.name for c in classes} & {f.name for f in funcdefs}):
      # TODO: raise a syntax error right when the identifier is defined.
      raise make_syntax_error(self, 'Duplicate identifier(s)', p)
    p[0] = pytd.TypeDeclUnit(constants=constants,
                             functions=MergeSignatures(funcdefs),
                             classes=classes,
                             modules={})

  def p_alldefs_constant(self, p):
    """alldefs : alldefs constantdef"""
    p[0] = p[1] + [p[2]]

  def p_alldefs_class(self, p):
    """alldefs : alldefs classdef"""
    p[0] = p[1] + [p[2]]

  def p_alldefs_func(self, p):
    """alldefs : alldefs funcdef"""
    p[0] = p[1] + [p[2]]

  def p_alldefs_null(self, p):
    """alldefs :"""
    p[0] = []

  # TODO(raoulDoc): doesn't support nested classes
  # TODO: parents is redundant -- should match what's in .py file
  def p_classdef(self, p):
    """classdef : CLASS template NAME parents COLON INDENT class_funcs DEDENT"""
    #             1     2        3    4       5     6
    # TODO: do name lookups for template within class_funcs
    funcdefs = [x for x in p[7] if isinstance(x, NameAndSig)]
    constants = [x for x in p[7] if isinstance(x, pytd.Constant)]
    if (set(f.name for f in funcdefs) | set(c.name for c in constants) !=
        set(d.name for d in p[7])):
      # TODO: raise a syntax error right when the identifier is defined.
      raise make_syntax_error(self, 'Duplicate identifier(s)', p)
    p[0] = pytd.Class(name=p[3], parents=p[4],
                      methods=MergeSignatures(funcdefs),
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
    p[0] = p[1] + [pytd.NamedType(p[3])]

  def p_parent_list_1(self, p):
    """parent_list : NAME"""
    p[0] = [pytd.NamedType(p[1])]

  def p_template(self, p):
    """template : LBRACKET templates RBRACKET"""
    p[0] = p[2]

  def p_template_null(self, p):
    """template : """  # pylint: disable=g-short-docstring-space
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
    p[0] = pytd.TemplateItem(p[1], pytd.NamedType('object'), 0)

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
    p[0] = pytd.Constant(p[1], p[3])

  def p_funcdef(self, p):
    """funcdef : provenance DEF template NAME LPAREN params RPAREN return raises signature"""
    #            1          2   3        4     5     6      7      8      9     10
    # TODO: do name lookups for template within params, return, raises
    # TODO: Output a warning if we already encountered a signature
    #              with these types (but potentially different argument names)
    signature = pytd.Signature(params=tuple(p[6].required), return_type=p[8],
                               exceptions=tuple(p[9]), template=tuple(p[3]),
                               has_optional=p[6].has_optional, provenance=p[1])
    p[0] = NameAndSig(name=p[4], signature=signature)

  def p_return(self, p):
    """return : ARROW compound_type"""
    p[0] = p[2]

  # We interpret a missing "-> type" as: "Type not specified"
  def p_return_null(self, p):
    """return :"""
    p[0] = pytd.NamedType('object')

  def p_params_multi(self, p):
    """params : params COMMA param"""
    p[0] = Params(p[1].required + [p[3]], has_optional=False)

  def p_params_ellipsis(self, p):
    """params : params COMMA DOT DOT DOT"""
    p[0] = Params(p[1].required, has_optional=True)

  def p_params_1(self, p):
    """params : param"""
    p[0] = Params([p[1]], has_optional=False)

  def p_params_only_ellipsis(self, p):
    """params : DOT DOT DOT"""
    p[0] = Params([], has_optional=True)

  def p_params_null(self, p):
    """params :"""
    p[0] = Params([], has_optional=False)

  def p_param(self, p):
    """param : NAME"""
    # type is optional and defaults to "object"
    p[0] = pytd.Parameter(p[1], pytd.NamedType('object'))

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
    p[0] = p[1]

  def p_identifier_name(self, p):
    """identifier : NAME"""
    p[0] = pytd.NamedType(p[1])

  def p_identifier_string(self, p):
    """identifier : STRING"""
    p[0] = pytd.Scalar(p[1])

  def p_identifier_number(self, p):
    """identifier : NUMBER"""
    p[0] = pytd.Scalar(p[1])

  def p_compound_type_and(self, p):
    """compound_type : compound_type AND compound_type"""
    # TODO: Unless we bring interfaces back, it's not clear when
    #              "type1 and type2" would be useful for anything. We
    #              should remove it.
    # This rule depends on precedence specification
    if (isinstance(p[1], pytd.IntersectionType) and
        isinstance(p[3], pytd.NamedType)):
      p[0] = pytd.IntersectionType(p[1].type_list + (p[3],))
    elif (isinstance(p[1], pytd.NamedType) and
          isinstance(p[3], pytd.IntersectionType)):
      # associative
      p[0] = pytd.IntersectionType(((p[1],) + p[3].type_list))
    else:
      p[0] = pytd.IntersectionType((p[1], p[3]))

  def p_compound_type_or(self, p):
    """compound_type : compound_type OR compound_type"""
    # This rule depends on precedence specification
    if (isinstance(p[1], pytd.UnionType) and
        isinstance(p[3], pytd.NamedType)):
      p[0] = pytd.UnionType(p[1].type_list + (p[3],))
    elif (isinstance(p[1], pytd.NamedType) and
          isinstance(p[3], pytd.UnionType)):
      # associative
      p[0] = pytd.UnionType((p[1],) + p[3].type_list)
    else:
      p[0] = pytd.UnionType((p[1], p[3]))

  # This is parameterized type
  # TODO(raoulDoc): support data types in future?
  # data  Tree a  =  Leaf a | Branch (Tree a) (Tree a)
  # TODO(raoulDoc): should we consider nested generics?

  # TODO: for generic types, we explicitly don't allow
  #                  compound_type<...> but insist on identifier<...> ... this
  #                  is because the grammar would be ambiguous, but for some
  #                  reason PLY didn't come up with a shift/reduce conflict but
  #                  just quietly promoted OR and AND above LBRACKET
  #                  (or, at least, that's what I think happened). Probably best
  #                  to not use precedence and write everything out fully, even
  #                  if it's a more verbose grammar.

  def p_compound_type_homogeneous(self, p):
    """compound_type : identifier LBRACKET parameters RBRACKET"""
    if len(p[3]) == 1:
      element_type, = p[3]
      p[0] = pytd.HomogeneousContainerType(base_type=p[1],
                                           element_type=element_type)
    else:
      p[0] = pytd.GenericType(base_type=p[1], parameters=p[3])

  def p_compound_type_generic_1(self, p):
    """compound_type : identifier LBRACKET parameters COMMA RBRACKET"""
    p[0] = pytd.GenericType(base_type=p[1], parameters=p[3])

  def p_compound_type_paren(self, p):
    """compound_type : LPAREN compound_type RPAREN"""
    p[0] = p[2]

  def p_compound_type_identifier(self, p):
    """compound_type : identifier"""
    p[0] = p[1]

  def p_parameters_1(self, p):
    """parameters : parameter"""
    p[0] = (p[1],)

  def p_parameters_multi(self, p):
    """parameters : parameters COMMA parameter"""
    p[0] = p[1] + (p[3],)

  def p_parameter(self, p):
    """parameter : compound_type"""
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


def parse_file(filename):
  with open(filename) as f:
    try:
      return PyParser().Parse(f.read(), filename)
    except SyntaxError as unused_exception:
      # without all the tedious traceback stuff from PLY:
      # TODO: What happens if we don't catch SyntaxError?
      traceback.print_exception(sys.exc_type, sys.exc_value, None)
      sys.exit(1)

