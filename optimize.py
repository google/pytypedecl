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


"""Functions for optimizing pytd parse trees and ASTs."""

import collections

from pytypedecl import pytd


def MergeSignatures(names_and_signatures):
  """Given a list of pytd function signature declarations, group them by name.

  Converts a list of NameAndSignature items to a list of Functions (grouping
  signatures by name).

  Arguments:
    names_and_signatures: A list of tuples (name, signature).

  Returns:
    A list of instances of pytd.Function.
  """
  # TODO: move this code into parse/parser.py

  name_to_signatures = collections.defaultdict(list)

  for name, signature in names_and_signatures:
    name_to_signatures[name].append(signature)

  # TODO: Return this as a dictionary.
  return [pytd.Function(name, signatures)
          for name, signatures in name_to_signatures.viewitems()]
