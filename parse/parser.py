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

# TODO: add support for constants and functions

# pylint: disable=g-bad-name, g-short-docstring-punctuation
# pylint: disable=g-doc-args, g-no-space-after-docstring-summary
# pylint: disable=g-space-before-docstring-summary
# pylint: disable=g-backslash-continuation

import ply.lex as lex
import ply.yacc as yacc
from pytypedecl.parse import ast
from pytypedecl.parse import typing


class PyLexer(object):
  """Lexer for type declaration language."""

  def __init__(self):
    self.lexer = lex.lex(module=self, debug=False)
    self.lexer.escaping = False

  t_ARROW = r'->'
  t_CLASS = r'class'
  t_COLON = r':'
  t_COMMA = r','
  t_DEF = r'def'
  t_DOT = r'\.'
  t_EQUALS = r'='
  t_INTERFACE = r'interface'
  t_INTERSECT = r'&'
  t_LBRACKET = r'\['
  t_LPAREN = r'\('
  t_NEWLINE = r'\n'  # TODO: [unused] figure out how to do this
  t_QUESTION = r'\?'
  t_RAISES = r'raises'
  t_RBRACKET = r'\]'
  t_RPAREN = r'\)'
  t_UNION = r'\|'

  reserved = {
      t_CLASS: 'CLASS',
      t_DEF: 'DEF',
      t_INTERFACE: 'INTERFACE',
      t_RAISES: 'RAISES',
  }

  tokens = [
      'ARROW',
      'COLON',
      'COMMA',
      'COMMENT',  # TODO: Currently unused
      'DOT',      # TODO: Currently unused
      'EQUALS',   # TODO: Currently unused
      'INTERSECT',
      'LBRACKET',
      'LPAREN',
      'NAME',
      'NEWLINE',  # TODO: Currently unused
      'NUMBER',
      'QUESTION',
      'RBRACKET',
      'RPAREN',
      'STRING',
      'UNION',
  ] + list(reserved.values())

  # Ignored characters
  t_ignore = ' \t'

  def t_NAME(self, t):
    r"""([a-zA-Z_][a-zA-Z0-9_\.]*)|""" \
    r"""(`[^`]*`)"""
    # TODO: Add a n'...' form to allow names that match a keyword
    # (or names with illegal characters) ... perhaps use `...` (note that n'...'
    # doesn't work because it's not distinguishable from "n '...'" unless more
    # cleverness is put into the tokenizer to do a 1-lookahead).
    if t.value[0] == r'`':
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
    self.lexer = PyLexer()
    self.tokens = self.lexer.tokens
    self.parser = yacc.yacc(
        module=self,
        # TODO: Instead of using write_tables, debug= here,
        #                  there should be a separate build step that generates
        #                  the tables file and the parser simply reads it for
        #                  production use. (With a suitable flag to __init__
        #                  and a flag to main.)
        write_tables=False,   # TODO: outputdir=..., tabmodule=...
        debug=False,
        # comment out the following line to get warnings from PLY such as
        # reduce/reduce conflicts (also set debug=True):
        errorlog=yacc.NullLogger(),
        **kwargs)

  def Parse(self, data, **kwargs):
    return self.parser.parse(data, **kwargs)

  def p_defs(self, p):
    """defs : funcdefs classdefs interfacedefs
    """
    # TODO: change to def : funcdef | classdef | interfacedef
    #                            defs : defs def | defs
    #        (this will require handling indent/exdent and/or allowing {...}
    p[0] = ast.PyOptTypeDeclUnit(p[3], p[2], p[1])

  def p_classdefs_null(self, p):
    """classdefs :"""
    p[0] = ast.PyOptClassDefs([])

  def p_classdefss(self, p):
    """classdefs : classdefs classdef"""
    p[1].AddClassDef(p[2])
    p[0] = p[1]

  # TODO(rgurma): doesn't support nested classes
  def p_classdef(self, p):
    """classdef : CLASS NAME COLON class_funcs"""
    p[0] = ast.PyOptClassDef(p[2], p[4])

  def p_class_funcs_null(self, p):
    """class_funcs :"""
    p[0] = ast.PyOptFuncDefs([])

  def p_class_funcs(self, p):
    """class_funcs : class_funcs funcdef"""
    p[1].AddFuncDef(p[2])
    p[0] = p[1]

  def p_interfacedefs_null(self, p):
    """interfacedefs :"""
    p[0] = ast.PyOptInterfaceDefs([])

  def p_interfacedefs(self, p):
    """interfacedefs : interfacedefs interfacedef
    """
    p[1].AddInterfaceDef(p[2])
    p[0] = p[1]

  def p_interfacedef(self, p):
    """interfacedef : INTERFACE NAME interface_parents COLON interface_attrs"""
    p[0] = ast.PyOptInterfaceDef(p[2], p[3], p[5])

  def p_interface_parents_null(self, p):
    """interface_parents :"""
    p[0] = []

  def p_interface_parents(self, p):
    """interface_parents : LPAREN parent_list RPAREN"""
    p[0] = p[2]

  def p_parent_list_1(self, p):
    """parent_list : NAME"""
    p[0] = [p[1]]

  def p_parent_list_multi(self, p):
    """parent_list : parent_list COMMA NAME"""
    p[1].append(p[3])
    p[0] = p[1]

  # TODO(rgurma): support signatures in interfaces
  def p_interface_attrs(self, p):
    """interface_attrs : interface_attrs DEF NAME"""
    p[1].append(p[3])
    p[0] = p[1]

  def p_interface_attrs_null(self, p):
    """interface_attrs : DEF NAME"""
    p[0] = [p[2]]

  # TODO(rgurma): doesn't support nested functions
  def p_funcdefs_null(self, p):
    """funcdefs :"""
    p[0] = ast.PyOptFuncDefs([])

  def p_funcdefs(self, p):
    """funcdefs : funcdefs funcdef"""
    p[1].AddFuncDef(p[2])
    p[0] = p[1]

  def p_funcdef(self, p):
    """funcdef : DEF NAME LPAREN params RPAREN ARROW compound_type raises"""
    p[0] = ast.PyOptFuncDef(p[2], p[4], p[7], p[8])

  def p_params_multi(self, p):
    """params : params COMMA param"""
    p[1].append(p[3])
    p[0] = p[1]

  def p_params_1(self, p):
    """params : param"""
    p[0] = [p[1]]

  def p_params_empty(self, p):
    """params :"""
    p[0] = []

  def p_param(self, p):
    """param : NAME"""
    # type can be optional if we don't want to typecheck
    p[0] = ast.PyOptParam(p[1], typing.UnknownType())

  def p_param_and_type(self, p):
    """param : NAME COLON compound_type"""
    p[0] = ast.PyOptParam(p[1], p[3])

  def p_raises(self, p):
    """raises : RAISES exceptions"""
    p[0] = p[2]

  def p_raises_null(self, p):
    """raises :"""
    p[0] = []

  def p_exceptions_1(self, p):
    """exceptions : exception"""
    p[0] = [p[1]]

  def p_exceptions_multi(self, p):
    """exceptions : exceptions COMMA exception"""
    p[1].append(p[3])
    p[0] = p[1]

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
    p[1].AddType(p[3])
    p[0] = p[1]

  def p_union_type_1(self, p):
    """union_type : identifier"""
    # Create UnionType only if more than one identifier
    p[0] = typing.UnionType([p[1]])

  def p_intersection_type_multi(self, p):
    """intersection_type : intersection_type INTERSECT identifier"""
    p[1].AddType(p[3])
    p[0] = p[1]

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
    p[1].AddType(p[3])
    p[0] = p[1]

  def p_compound_type_intersection(self, p):
    """compound_type : intersection_type INTERSECT identifier"""
    p[1].AddType(p[3])
    p[0] = p[1]

  def p_compound_type_identifier(self, p):
    """compound_type : identifier"""
    p[0] = p[1]

  def p_error(self, p):
    raise SyntaxError("Syntax error at '%s'" % repr(p))
