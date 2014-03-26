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


"""Add more stringent equality test to collections.namedtuple.

The Eq class is a mixin for verifying that the two collections.namedtuple items
being tested for equality are of the same class.

See ast_type.py for how to use.

See http://bugs.python.org/issue16279 for why this is unlikely to be made part
of collections.namedtuple.
"""


class Eq(object):
  """Mixin for adding class equality to collections.namedtuple equality.

  It assumes that it is used with a class that was defined by
  collections.namedtuple (this is *not* verified).

  collections.namedtuple.__eq__ is implicitly tuple equality (which makes two
  tuples equal if all their values are recursively equal), but that allows two
  objects to be the same if they happen to have the same field values. To avoid
  this problem, you can mixin TupleEq, which adds the check that the two
  objects' classes are equal (this might be too strong, in which case you'd need
  to use isinstance checks). This mixin must be *first* to ensure it takes
  precedence of tuple.__eq__ (or define your own __eq__ using super(); same for
  __ne__).

  """

  def __eq__(self, other):
    if self.__class__ is other.__class__:
      return tuple.__eq__(self, other)
    else:
      return NotImplemented

  def __ne__(self, other):
    if self.__class__ is other.__class__:
      return tuple.__ne__(self, other)
    else:
      # TODO: This is inconsistent with __eq__ (NoImplemented <-> True)
      return True
