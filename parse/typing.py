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


"""Different kinds of types for the parser and typechecker.

Each type has a Process method that takes a 'processor', which implements the
necessary callbacks. In this way, the processor can keep state, and can be used
to do node-specific processing, such as pretty-printing or creating constraints.
Typically, the caller will walk the tree and call itself via the Process
method. For example:

    class Printer(object):

      def WalkFunc(self, func):
        Print(func.name, ', '.join(p.type.Process(self) for p in func.params))

      # The Process callbacks:

      def ProcessBasicType(self, t):
        return t.containing_type

      def ProcessUnionType(self, t):
        return 'UNION({})'.format(', '.join(
            u.Process(self) for u in t.type_list))

      ... etc. ...
"""


# TODO: The AddType methods smash an existing item on the parse tree
#                  ... change to something like:
#                  def AppendType(self, t):
#                    return type(self)(self.type_list + t)


import collections
from pytypedecl.parse import typed_tuple


class BasicType(typed_tuple.Eq, collections.namedtuple(
    'BasicType', ['containing_type'])):

  def Process(self, processor):
    return processor.ProcessBasicType(self)


class ConstType(typed_tuple.Eq, collections.namedtuple(
    'ConstType', ['value'])):

  def Process(self, processor):
    return processor.ProcessConstType(self)


class NoneAbleType(typed_tuple.Eq, collections.namedtuple(
    'NoneAbleType', ['base_type'])):

  def Process(self, processor):
    return processor.ProcessNonableType(self)


class UnionType(typed_tuple.Eq, collections.namedtuple(
    'UnionType', ['type_list'])):

  def Process(self, processor):
    return processor.ProcessUnionType(self)

  def AddType(self, type_element):
    self.type_list.append(type_element)


class IntersectionType(typed_tuple.Eq, collections.namedtuple(
    'IntersectionType', ['type_list'])):

  def Process(self, processor):
    return processor.ProcessIntersectionType(self)

  def AddType(self, type_element):
    self.type_list.append(type_element)


class StructType(typed_tuple.Eq, collections.namedtuple(
    'StructType', ['ops'])):

  def Process(self, processor):
    return processor.ProcessStructType(self)

  # Extra initialition ... see
  # http://stackoverflow.com/questions/3624753/how-to-provide-additional-initialization-for-a-subclass-of-namedtuple

  def __new__(cls, ops):
    return super(StructType, cls).__new__(cls, sorted(set(ops)))


class GenericType1(typed_tuple.Eq, collections.namedtuple(
    'GenericType1', ['base_type', 'type1'])):

  def Process(self, processor):
    return processor.ProcessGenericType1(self)


class GenericType2(typed_tuple.Eq, collections.namedtuple(
    'GenericType2', ['base_type', 'type1', 'type2'])):
  """Constructor for types taking two type arguments.

  Attributes:
    base_type: type that is parameterized. E.g. dict
    type1: first type parameter. E.g. dict[type1, type2]
    type2: second type parameter. E.g. dict[type1, type2]
  """

  def Process(self, processor):
    return processor.ProcessGenericType1(self)


class UnknownType(typed_tuple.Eq, collections.namedtuple('UnkownType', '')):
  pass
