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

# NOTE(rgurma): the naming scheme of 'tokens' and 'states', 't_*', 'p_*'
# variables/functions below are specially required by ply.yacc and ply.lex. We
# have to give up Google Python coding style in order to use them.
# Also, must use backslash-continuation to combine docstrings

# TODO: look at https://github.com/JetBrains/python-skeletons
#                  for an alternative syntax (e.g. T <= Foo for T such
#                  that it's Foo or subclass) ... doesn't have interfaces
#                  or intersection

# pylint: disable=g-bad-name, g-short-docstring-punctuation
# pylint: disable=g-doc-args, g-no-space-after-docstring-summary
# pylint: disable=g-space-before-docstring-summary
# pylint: disable=g-backslash-continuation

import sys
from ply import lex
from ply import yacc
from pytypedecl.parse import ast
from pytypedecl.parse import typing


class PyLexer(object):
  """Lexer for type declaration language."""

  def __init__(self):
    # TODO: See comments with PyParser about generating the
    #                  $GENFILESDIR/pytypedecl_lexer.py and using it by
    #                  calling lex.lex(lextab=pytypedecl_lexer)
    self.lexer = lex.lex(module=self, debug=False)
    self.lexer.escaping = False

  t_ARROW = r'->'
  t_AT = r'@'
  t_CLASS = r'class'
  t_COLON = r':'
  t_COMMA = r','
  t_DEF = r'def'
  t_DOT = r'\.'
  t_INTERFACE = r'interface'
  t_INTERSECT = r'&'
  t_LBRACKET = r'\['
  t_LPAREN = r'\('
  t_MINUS = r'-'
  t_PLUS = r'\+'
  t_QUESTION = r'\?'
  t_RAISE = r'raise'
  t_RBRACKET = r'\]'
  t_RPAREN = r'\)'
  t_SUBCLASS = r'<='  # or '<:' - notation from Scala, type theory
  t_UNION = r'\|'

  reserved = {
      t_CLASS: 'CLASS',
      t_DEF: 'DEF',
      t_INTERFACE: 'INTERFACE',
      t_RAISE: 'RAISE',
  }

  tokens = [
      'ARROW',
      'AT',
      'COLON',
      'COMMA',
      # 'COMMENT',  # Not used in the grammar; only used to discard comments
      'DOT',
      'INTERSECT',
      'LBRACKET',
      'LPAREN',
      'MINUS',
      'NAME',
      'NUMBER',
      'PLUS',
      'QUESTION',
      'RBRACKET',
      'RPAREN',
      'STRING',
      'SUBCLASS',
      'UNION',
  ] + list(reserved.values())

  # Ignored characters
  t_ignore = ' \t'

  # Start symbol
  start = 'defs'

  def t_NAME(self, t):
    r"""([a-zA-Z_][a-zA-Z0-9_\.]*)|""" \
    r"""(`[^`]*`)"""
    # This defines a token of the form `...`, to allow names that are keywords
    # in pytd syntax.
    if t.value[0] == r'`':
      assert t.value[-1] == r'`'  # from regexp
      t.value = t.value[1:-1]
      t.type = 'NAME'
    else:
      t.type = self.reserved.get(t.value, 'NAME')
    return t

  def t_STRING(self, t):
    r"""'([^']|\\')*'|""" \
    r'"([^"]|\\")*"'
    # TODO: full Python string syntax (e.g., """...""", r"...")
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
    raise SyntaxError("Illegal character '%s'" % t.value[0])


class PyParser(object):
  """Parser for type declaration language."""

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
        module=self,
        debug=False,
        # debuglog=yacc.PlyLogger(sys.stderr),
        # errorlog=yacc.NullLogger(),  # If you really want to suppress messages
        **kwargs)

  def Parse(self, data, **kwargs):
    return self.parser.parse(data, **kwargs)

  def p_defs(self, p):
    """defs : funcdefs classdefs interfacedefs
    """
    # TODO: change the definition of defs to:
    #            defs : defs def | defs
    #            def : funcdef | classdef | interfacedef
    #        This will require handling indent/exdent and/or allowing {...}.
    #        Also requires supporting INDENT/DEDENT because otherwise it's
    #        ambiguous on the meaning of a funcdef after a classdef
    p[0] = ast.PyOptTypeDeclUnit(p[3], p[2], p[1])

  def p_classdefs(self, p):
    """classdefs : classdefs classdef"""
    p[0] = p[1] + [p[2]]

  def p_classdefs_null(self, p):
    """classdefs :"""
    p[0] = []

  # TODO(rgurma): doesn't support nested classes
  # TODO: parents is redundant -- should match what's in .py file
  #                  but is here for compatibility with INTERFACE
  def p_classdef(self, p):
    """classdef : CLASS template NAME parents COLON class_funcs"""
    #             1     2        3    4       5     6
    p[0] = ast.PyOptClassDef(name=p[3], parents=p[4], funcs=p[6], template=p[2])

  def p_class_funcs(self, p):
    """class_funcs : class_funcs funcdef"""
    p[0] = p[1] + [p[2]]

  def p_class_funcs_null(self, p):
    """class_funcs :"""
    p[0] = []

  def p_interfacedefs(self, p):
    """interfacedefs : interfacedefs interfacedef
    """
    p[0] = p[1] + [p[2]]

  def p_interfacedefs_null(self, p):
    """interfacedefs :"""
    p[0] = []

  def p_interfacedef(self, p):
    """interfacedef : INTERFACE template NAME parents COLON interface_attrs"""
    #                 1         2        3    4       5     6
    p[0] = ast.PyOptInterfaceDef(
        name=p[3], parents=p[4], attrs=p[6], template=p[2])

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
    p[0] = p[1]

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
    p[0] = ast.PyTemplateItem(p[1], typing.BasicType('None'))

  def p_template_item_subclss(self, p):
    """template_item : NAME SUBCLASS compound_type"""
    p[0] = ast.PyTemplateItem(p[1], p[3])

  # TODO(rgurma): support signatures in interfaces
  def p_interface_attrs(self, p):
    """interface_attrs : interface_attrs DEF NAME"""
    p[0] = p[1] + [p[3]]

  def p_interface_attrs_null(self, p):
    """interface_attrs : DEF NAME"""
    p[0] = [p[2]]

  def p_funcdefs(self, p):
    """funcdefs : funcdefs funcdef"""
    p[0] = p[1] + [p[2]]

  # TODO(rgurma): doesn't support nested functions
  def p_funcdefs_null(self, p):
    """funcdefs :"""
    p[0] = []

  def p_funcdef(self, p):
    """funcdef : provenance DEF template NAME LPAREN params RPAREN return raise signature"""
    #            1          2   3        4     5     6      7      8      9     10
    p[0] = ast.PyOptFuncDef(name=p[4], params=p[6], return_type=p[8],
                            exceptions=p[9], template=p[3], provenance=p[1],
                            signature=p[10])

  def p_return(self, p):
    """return : ARROW compound_type"""
    p[0] = p[2]

  def p_return_null(self, p):
    """return :"""
    p[0] = typing.BasicType('None')

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
    # type can be optional if we don't want to typecheck
    p[0] = ast.PyOptParam(p[1], typing.UnknownType())

  def p_param_and_type(self, p):
    """param : NAME COLON compound_type"""
    p[0] = ast.PyOptParam(p[1], p[3])

  def p_raise(self, p):
    """raise : RAISE exceptions"""
    p[0] = p[2]

  def p_raise_null(self, p):
    """raise :"""
    p[0] = []

  def p_exceptions_1(self, p):
    """exceptions : exception"""
    p[0] = [p[1]]

  def p_exceptions_multi(self, p):
    """exceptions : exceptions COMMA exception"""
    p[0] = p[1] + [p[3]]

  def p_exception(self, p):
    """exception : identifier"""
    p[0] = ast.PyOptException(p[1])

  def p_identifier_name_optional(self, p):
    """identifier : NAME QUESTION"""
    p[0] = typing.NoneAbleType(typing.BasicType(p[1]))

  def p_identifier_name(self, p):
    """identifier : NAME"""
    p[0] = typing.BasicType(p[1])

  def p_identifier_string(self, p):
    """identifier : STRING"""
    p[0] = typing.ConstType(p[1])

  def p_identifier_number(self, p):
    """identifier : NUMBER"""
    p[0] = typing.ConstType(p[1])

  def p_union_type_multi(self, p):
    """union_type : union_type UNION identifier"""
    p[0] = typing.AppendedTypeList(p[1], p[3])

  def p_union_type_1(self, p):
    """union_type : identifier"""
    # Create UnionType only if more than one identifier
    p[0] = typing.UnionType([p[1]])

  def p_intersection_type_multi(self, p):
    """intersection_type : intersection_type INTERSECT identifier"""
    p[0] = typing.AppendedTypeList(p[1], p[3])

  def p_intersection_type_1(self, p):
    """intersection_type : identifier"""
    # Create IntersectionType only if more than one identifier
    p[0] = typing.IntersectionType([p[1]])

  # This is parameterized type
  # TODO(rgurma): support data types in future?
  # data  Tree a  =  Leaf a | Branch (Tree a) (Tree a)
  # TODO(rgurma): restricted to 2 params on purpose
  # might want to extend in future if there are use cases
  # TODO(rgurma): should we consider nested generics?

  def p_generic_type_1(self, p):
    """generic_type : identifier LBRACKET identifier RBRACKET"""
    p[0] = typing.GenericType1(p[1], p[3])

  def p_generic_type_2(self, p):
    """generic_type : identifier LBRACKET identifier COMMA identifier RBRACKET
    """
    p[0] = typing.GenericType2(p[1], p[3], p[5])

  def p_compound_type_generic(self, p):
    """compound_type : generic_type"""
    p[0] = p[1]

  def p_compound_type_union(self, p):
    """compound_type : union_type UNION identifier"""
    p[0] = typing.AppendedTypeList(p[1], p[3])

  def p_compound_type_intersection(self, p):
    """compound_type : intersection_type INTERSECT identifier"""
    p[0] = typing.AppendedTypeList(p[1], p[3])

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
    # TODO: Improve the error output
    raise SyntaxError("Syntax error at '%s'" % repr(p))
