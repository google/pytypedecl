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

The ExpandTemplates method is used to look up names in the AST and replace them
by ast.PyTemplateItem from the look-up. The 'rev_templates' argument is the list
of templates in reverse order (most recent one first).

"""


import collections
from pytypedecl.parse import typed_tuple


class BasicType(typed_tuple.Eq, collections.namedtuple(
    'BasicType', ['containing_type'])):

  def ExpandTemplates(self, rev_templates):
    for level, templ in enumerate(rev_templates):
      for t in templ:
        if self.containing_type == t.name:
          return t._replace(level=level)  # PyTemplateItem
    else:
      return self

  def Process(self, processor):
    return processor.ProcessBasicType(self)


class ConstType(typed_tuple.Eq, collections.namedtuple(
    'ConstType', ['value'])):

  def ExpandTemplates(self, unused_rev_templates):
    return self

  def Process(self, processor):
    return processor.ProcessConstType(self)


class NoneAbleType(typed_tuple.Eq, collections.namedtuple(
    'NoneAbleType', ['base_type'])):

  def ExpandTemplates(self, unused_rev_templates):
    return self

  def Process(self, processor):
    return processor.ProcessNonableType(self)


class UnionType(typed_tuple.Eq, collections.namedtuple(
    'UnionType', ['type_list'])):

  def ExpandTemplates(self, rev_templates):
    return self._replace(
        type_list=[t.ExpandTemplates(rev_templates) for t in self.type_list])

  def Process(self, processor):
    return processor.ProcessUnionType(self)


class IntersectionType(typed_tuple.Eq, collections.namedtuple(
    'IntersectionType', ['type_list'])):

  def ExpandTemplates(self, rev_templates):
    return self._replace(
        type_list=[t.ExpandTemplates(rev_templates) for t in self.type_list])

  def Process(self, processor):
    return processor.ProcessIntersectionType(self)


class StructType(typed_tuple.Eq, collections.namedtuple(
    'StructType', ['ops'])):

  # There's no ExpandTemplates method because StructType isn't
  # created by the parser.

  def Process(self, processor):
    return processor.ProcessStructType(self)

  # Extra initialization ... see
  # http://stackoverflow.com/questions/3624753/how-to-provide-additional-initialization-for-a-subclass-of-namedtuple

  def __new__(cls, ops):
    return super(StructType, cls).__new__(cls, sorted(set(ops)))


class GenericType1(typed_tuple.Eq, collections.namedtuple(
    'GenericType1', ['base_type', 'type1'])):

  def ExpandTemplates(self, rev_templates):
    return self._replace(
        base_type=self.base_type.ExpandTemplates(rev_templates),
        type1=self.type1.ExpandTemplates(rev_templates))

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

  def ExpandTemplates(self, rev_templates):
    return self._replace(
        base_type=self.base_type.ExpandTemplates(rev_templates),
        type1=self.type1.ExpandTemplates(rev_templates),
        type2=self.type2.ExpandTemplates(rev_templates))

  def Process(self, processor):
    return processor.ProcessGenericType1(self)


class UnknownType(typed_tuple.Eq, collections.namedtuple('UnknownType', '')):

  def ExpandTemplates(self, unused_rev_templatesn):
    return self

  def Process(self, processor):
    return processor.ProcessUnknownType(self)


def AppendedTypeList(base, added_type):
  """New instance with one more item on the type_list."""
  # pylint: disable=protected-access
  return base._replace(type_list=base.type_list + [added_type])
