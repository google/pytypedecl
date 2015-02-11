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


"""Utilities for pytypedecl.

This provides a utility function to access data files in a way that works either
locally or within a larger repository.
"""

import collections
import os


from pytypedecl import pytd


def GetDataFile(filename=""):
    full_filename = os.path.abspath(
        os.path.join(os.path.dirname(pytd.__file__), filename))
    with open(full_filename, "rb") as fi:
      return fi.read()


def UnpackUnion(t):
  """Return the type list for union type, or a list with the type itself."""
  if isinstance(t, pytd.UnionType):
    return t.type_list
  else:
    return [t]


def Concat(pytd1, pytd2):
  """Concatenate two pytd ASTs."""
  assert isinstance(pytd1, pytd.TypeDeclUnit)
  assert isinstance(pytd2, pytd.TypeDeclUnit)
  modules_union = {}
  modules_union.update(pytd1.modules)
  modules_union.update(pytd2.modules)
  return pytd.TypeDeclUnit(constants=pytd1.constants + pytd2.constants,
                           classes=pytd1.classes + pytd2.classes,
                           functions=pytd1.functions + pytd2.functions,
                           modules=modules_union)


def JoinTypes(types):
  """Combine a list of types into a union type, if needed.

  Leaves singular return values alone, or wraps a UnionType around them if there
  are multiple ones, or if there are no elements in the list (or only
  NothingType) return NothingType.

  Arguments:
    types: A list of types. This list might contain other UnionTypes. If
    so, they are flattened.

  Returns:
    A type that represents the union of the types passed in. Order is preserved.
  """
  queue = collections.deque(types)
  seen = set()
  new_types = []
  while queue:
    t = queue.popleft()
    if isinstance(t, pytd.UnionType):
      queue.extendleft(reversed(t.type_list))
    elif isinstance(t, pytd.NothingType):
      pass
    elif t not in seen:
      new_types.append(t)
      seen.add(t)

  if len(new_types) == 1:
    return new_types.pop()
  elif any(isinstance(t, pytd.UnknownType) for t in new_types):
    return pytd.UnknownType()
  elif new_types:
    return pytd.UnionType(tuple(new_types))  # tuple() to make unions hashable
  else:
    return pytd.NothingType()

