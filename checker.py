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


"""Module to handle type checking.
"""


from __future__ import print_function

import inspect
import itertools
import sys
import types
from pytypedecl.parse import typing
from pytypedecl.parse import utils

_parse_utils = utils.ParserUtils()


def IsFunctionInModule(function, module):
  return inspect.isfunction(function) and inspect.getmodule(function) == module


def Functions(module):
  return ((func.__name__, func) for func in module.__dict__.itervalues()
          if IsFunctionInModule(func, module))


def Classes(module):
  return inspect.getmembers(module, inspect.isclass)


def MethodsForClass(cls):
  return inspect.getmembers(cls, inspect.ismethod)


class CheckTypeAnnotationError(Exception):
  """An exception encapsulating type checking errors.

     A list of error messages is passed to the constructor.
  """
  pass


def ParamTypeErrorMsg(func_name, p_name, actual_p, expected_t):
  return ("[TYPE_ERROR] Function: {f}, parameter: {p}"
          " => FOUND: {found:s} but EXPECTED: {expected:s}").format(
              f=func_name, p=p_name, found=actual_p, expected=expected_t)


def ReturnTypeErrorMsg(func_name, actual_t, expected_t):
  return ("[TYPE_ERROR] Function: {f}, returns {found:s} but "
          "EXPECTED {expected:s}").format(
              f=func_name, found=actual_t, expected=expected_t)


def ExceptionTypeErrorMsg(func_name, actual_e, expected_e):
  return ("[TYPE_ERROR] Function: {f}, raised {found:s} but "
          "EXPECTED one of {expected:s}").format(
              f=func_name, found=actual_e, expected=expected_e)


# TODO(rgurma): improve error message (actual args)
def OverloadingTypeErrorMsg(func_name):
  return ("[TYPE_ERROR] Function: {f}, overloading error "
          "no matching signature found").format(f=func_name)


def GeneratorGenericTypeErrorMsg(func_name, gen_to_wrap,
                                 iteration, actual_t, expected_t):
  return ("{} {!r} iteration #{} was a {} not an {}"
          .format(func_name,
                  gen_to_wrap,
                  iteration,
                  actual_t,
                  expected_t))


def _EvalWithModuleContext(expr, module):
  return eval(expr, module.__dict__)


def ConvertToType(module, interfaces, type_node):
  """Helper for converting a type node to a valid Python type.

  Args:
    module: The module to look up symbols/types
    interfaces: A dict of declared interfaces
    type_node: A type node to convert into a python type

  Returns:
    A valid Python type. Note that None is considered a type in
    the declaration language, but a value in Python. So a string
    None is converted to a NoneType. We use the module object to look
    up potential type definitions defined inside that module.

  Raises:
    TypeError: if the type node passed is not supported/unknown
  """
  # unknown type can be passed through
  if isinstance(type_node, typing.UnknownType):
    return type_node
  # clean up str
  if isinstance(type_node, typing.BasicType):
    if type_node.containing_type == "None":
      return types.NoneType
    elif type_node.containing_type == "generator":
      return types.GeneratorType
    elif type_node.containing_type in interfaces:
      ops = _GetListOpsForInterface(interfaces[type_node.containing_type],
                                    interfaces)
      return typing.StructType(ops)
    else:
      res = _EvalWithModuleContext(type_node.containing_type, module)
      assert isinstance(res, type), (type_node.containing_type, repr(res))
      return res

  elif isinstance(type_node, typing.NoneAbleType):
    return typing.NoneAbleType(ConvertToType(module, interfaces,
                                             type_node.base_type))

  elif isinstance(type_node, typing.UnionType):
    return typing.UnionType([ConvertToType(module, interfaces, t)
                             for t in type_node.type_list])

  elif isinstance(type_node, typing.IntersectionType):
    return typing.IntersectionType([ConvertToType(module, interfaces, t)
                                    for t in type_node.type_list])

  elif isinstance(type_node, typing.GenericType1):
    return typing.GenericType1(ConvertToType(module,
                                             interfaces,
                                             type_node.base_type),
                               ConvertToType(module,
                                             interfaces,
                                             type_node.type1))

  elif isinstance(type_node, typing.GenericType2):
    return typing.GenericType2(ConvertToType(module,
                                             interfaces,
                                             type_node.base_type),
                               ConvertToType(module,
                                             interfaces,
                                             type_node.type1),
                               ConvertToType(module,
                                             interfaces,
                                             type_node.type2))
  else:
    raise TypeError("Unknown type of type_node: {!r}".format(type_node))


# functools.wraps doesn't work on generators
def _WrapGenWithTypeCheck(func_name, gen_to_wrap, element_type):
  """Typechecking decorator for typed generators."""
  def _TypeCheckPipeGenerator():
    for iteration, elem in enumerate(gen_to_wrap):
      if not isinstance(elem, element_type):
        error_msg = GeneratorGenericTypeErrorMsg(func_name,
                                                 gen_to_wrap,
                                                 iteration + 1,
                                                 type(elem),
                                                 element_type)
        raise CheckTypeAnnotationError([error_msg])
      yield elem
  return _TypeCheckPipeGenerator()


# see: http://docs.python.org/2/reference/datamodel.html
# we use im_self to differentiate bound vs unbound methods
def _IsClassMethod(func):
  return hasattr(func, "im_self") and func.im_self


def IsCompatibleType(actual, formal):
  """Check compatibility of an expression with a type definition.

  Args:
    actual: an expression being evaluated
    formal: type expected for this expression

  Returns:
    A boolean whether the actual expression is compatible with
    the formal type definition

  Raises:
    TypeError: if a generic type is not supported
  """

  if isinstance(formal, typing.UnknownType):
    # we don't type check unknown type, let python deal with it
    return True
  if isinstance(formal, typing.StructType):
    # we check that all the interface operations are supported in actual
    actual_ops = dir(actual)
    return all(o in actual_ops for o in formal.ops)
  if isinstance(formal, typing.NoneAbleType):
    return (IsCompatibleType(actual, types.NoneType)
            or IsCompatibleType(actual, formal.base_type))
  if isinstance(formal, typing.UnionType):
    for t in formal.type_list:
      if IsCompatibleType(actual, t):
        return True
    return False
  if isinstance(formal, typing.IntersectionType):
    for t in formal.type_list:
      if not IsCompatibleType(actual, t):
        return False
    return True
  # check if base type matches
  # then check that all elements match too (e.g. a list[int])
  if isinstance(formal, typing.GenericType1):
    if isinstance(actual, formal.base_type):
      # we don't consume decorators, rather their elements are
      # typechecked on demand. See _Check function
      if not isinstance(actual, types.GeneratorType):
        return all(
            isinstance(e, formal.type1) for e in actual)
      return True
    return False
  # TODO(rgurma): GenericType2, assume only dict for now
  if isinstance(formal, typing.GenericType2):
    if not isinstance(actual, dict):
      raise TypeError("Only dict is supported for types with 2 type params")
    return all(
        isinstance(k, formal.type1) and isinstance(v, formal.type2)
        for k, v in actual.items())
  # Basic Type
  return isinstance(actual, formal)


def _GetParamTypeErrors(module, interfaces, func_sig, args):
  """Helper for checking actual params vs formal params signature.

  Args:
    module: The module to look up symbols/types
    interfaces: A list of declared interfaces
    func_sig: function definition (PyOptFuncDef)
    args: actual arguments passed to the function

  Returns:
    A list of potential type errors
  """
  params = ((p.name, p.type) for p in func_sig.params)
  param_cmp_types = ((name, args[i], ConvertToType(module, interfaces, t))
                     for i, (name, t) in enumerate(params))
  params_type_error_list = [ParamTypeErrorMsg(func_sig.name, n, type(p), t)
                            for n, p, t in param_cmp_types
                            if not IsCompatibleType(p, t)]

  return params_type_error_list


def _GetExceptionsTupleFromFuncSig(module, interfaces, func_sig):
  """Helper for extracting exceptions from a function definition.

  Args:
      module: The module to look up symbols/types
      interfaces: A list of declared interfaces
      func_sig: function definition

  Returns:
      a tuple of exceptions from the function definition
  """
  return tuple(ConvertToType(module, interfaces, e.name)
               for e in func_sig.exceptions)


def TypeCheck(module, interfaces, func, func_sigs):
  """Decorator for typechecking a function.

  Args:
    module: The module associated with the function to typecheck
    interfaces: A list of declared interfaces
    func: A function to typecheck
    func_sigs: signatures of the function (PyOptFuncDef)

  Returns:
    A decorated function with typechecking assertions
  """
  def Wrapped(*args, **kwargs):
    """Typecheck a function given its signature.

    Args:
      *args: Arguments passed to the function
      **kwargs: Key/Value arguments passed to the function

    Returns:
      The result of calling the function decorated with typechecking

    Raises:
      CheckTypeAnnotationError: Type errors were found
    """
    # TODO(rgurma): generalise single sig and multiple sig checking
    # to reuse code?
    # at the moment this implementation is convenient because for
    # single signature we stack the errors before raising them
    # for overloading we only have "no matching signature found"
    if len(func_sigs) == 1:
      func_sig = func_sigs[0]
      # need to copy args tuple into list so can modify individual arg
      # specfically we want to replace args with decorated variants
      mod_args = []

      # decorating all typed generators
      cache_of_generators = {}
      for i, actual in enumerate(args):
        # first check actual is a generator
        if isinstance(actual, types.GeneratorType):
          # resolve the param signature at the formal position i
          resolved_type = ConvertToType(module,
                                        interfaces,
                                        func_sig.params[i].type)
          # Was the generator defined as generic-typed?
          # TODO(rgurma): formal  may be a union, so need to extract
          # generator signature
          if isinstance(resolved_type, typing.GenericType1):
            # if yes replace generator with a decorated version
            # we check if we already created a decorated version
            # for cases such as foo(same_gen, same_gen)
            if actual not in cache_of_generators:
              new_gen = _WrapGenWithTypeCheck(func_sig.name,
                                              actual,
                                              resolved_type.type1)
              cache_of_generators[actual] = new_gen
            # get generator from cache
            mod_args.append(cache_of_generators[actual])
          else:
          # here we have an untyped generator
            mod_args.append(actual)
        else:
          mod_args.append(actual)
      # type checking starts here
      # checking params
      type_error_list = _GetParamTypeErrors(module,
                                            interfaces,
                                            func_sig,
                                            args)

      exception_tuple = _GetExceptionsTupleFromFuncSig(module,
                                                       interfaces,
                                                       func_sig)
      # checking exceptions
      # semantic is "may raise": function doesn't have to throw
      # an exception despite declaring it in its signature
      # we check for excptions caught that were
      # not explicitly declared in the signature
      try:
        # TODO(rgurma): get a better understanding of classmethod
        # Is there a way without removing the first argument?
        if _IsClassMethod(func):
          mod_args = mod_args[1:]
        res = func(*mod_args, **kwargs)
      except Exception as e:
        # check if the exception caught was explicitly declared
        if (not isinstance(e, CheckTypeAnnotationError) and
            not IsCompatibleType(e, exception_tuple)):
          type_error_list.append(ExceptionTypeErrorMsg(
              func_sig.name, type(e), exception_tuple))

          raise CheckTypeAnnotationError(type_error_list, e)
        raise  # rethrow exception to preserve program semantics
      else:
        # checking return type
        expected_return_type = ConvertToType(module,
                                             interfaces,
                                             func_sig.return_type)
        if not IsCompatibleType(res, expected_return_type):
          type_error_list.append(ReturnTypeErrorMsg(
              func_sig.name, type(res), expected_return_type))

        if type_error_list:
          raise CheckTypeAnnotationError(type_error_list)

        return res
   # overloading checking
    else:
      # TODO(rgurma): overloaded class method support
      # TODO(rgurma): support for overloaded typed generators
      param_sig_checked = ((func_sig,
                            _GetParamTypeErrors(module,
                                                interfaces,
                                                func_sig,
                                                args))
                           for func_sig in func_sigs)

      # filter parameter signatures that yield no type errors
      func_sig_candidates = [func_sig
                             for (func_sig, type_errors) in param_sig_checked
                             if not type_errors]
      # nothing? this means no good signatures: overloading error
      if not func_sig_candidates:
        raise CheckTypeAnnotationError(
            [OverloadingTypeErrorMsg(func_sigs[0].name)])

      # need to check return type and exceptions
      try:
        res = func(*args, **kwargs)
      except Exception as e:
        # Is the exception caught valid with at least one func sig?

        for func_sig in func_sig_candidates:
          if IsCompatibleType(e, _GetExceptionsTupleFromFuncSig(module,
                                                                interfaces,
                                                                func_sig)):
            raise

        raise CheckTypeAnnotationError(
            [OverloadingTypeErrorMsg(func_sigs[0].name)])
      else:
        # Is the return type valid with at least one func sig?
        for func_sig in func_sig_candidates:
          if IsCompatibleType(res,
                              ConvertToType(module,
                                            interfaces,
                                            func_sig.return_type)):
            return res

        raise CheckTypeAnnotationError(
            [OverloadingTypeErrorMsg(func_sigs[0].name)])

  Wrapped.__name__ = func.__name__
  Wrapped.__doc__ = func.__doc__
  Wrapped.__module__ = func.__module__
  return classmethod(Wrapped) if(_IsClassMethod(func)) else Wrapped


def _GetListOpsForInterface(interface, interfaces_dict):
  """Returns the list of operations of an interface (with inheritance).

  Args:
    interface: the interface name to look up
    interfaces_dict: a dictionary of interface name to PyOptInterfaceDef

  Returns:
    a set of operations supported by the interface (with inherited ops)
  """
  ops = list(interface.attrs)
  if interface.parents:
    for parent_name in interface.parents:
      ops.extend(_GetListOpsForInterface(interfaces_dict[parent_name],
                                         interfaces_dict))
  return frozenset(ops)


# TODO(rgurma): attach line number of functions/classes
def _PrintWarning(msg):
  print("(Warning)", msg, "not annotated", file=sys.stderr)


def _Check(module, interfaces, classes, functions):
  """TypeChecks a module.

  Args:
    module: the module to typecheck
    interfaces: list of interfaces parsed from the type declarations
    classes: list of classes parsed from the type declarations
    functions: list of functions parsed from the type declarations
  """

  # typecheck functions in module
  for f_name, f_def in Functions(module):
    if f_name in functions:
      module.__dict__[f_name] = TypeCheck(module,
                                          interfaces,
                                          f_def,
                                          functions[f_name])
    else:
      _PrintWarning(f_name)

  # typecheck methods in classes
  for c_name, c_def in Classes(module):
    if c_name in classes:
      functions_in_class = {f_name: list(g) for f_name, g
                            in itertools.groupby(
                                classes[c_name].funcs,
                                lambda f: f.name)}

      for f_name, f_def in MethodsForClass(c_def):
        if f_name in functions_in_class:
          setattr(c_def, f_name, TypeCheck(module,
                                           interfaces,
                                           f_def,
                                           functions_in_class[f_name]))
        else:
          _PrintWarning(c_name + "." + f_name)
    else:
      _PrintWarning(c_name)


def CheckFromFile(module, path):
  by_name = _parse_utils.LoadTypeDeclarationFromFile(path)
  _Check(module, by_name.interfaces, by_name.classes, by_name.funcs)


def CheckFromData(module, data):
  interfaces, classes, funcs = _parse_utils.LoadTypeDeclaration(data)
  _Check(module, interfaces, classes, funcs)
