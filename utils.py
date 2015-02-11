"""Utilities for pytypedecl.

This provides a utility function to access data files in a way that works either
locally or within a larger repository.
"""

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
