"""Utilities for pytypedecl.

This provides a utility function to access data files in a way that works either
locally or within a larger repository.
"""

import os


from pytypedecl import pytd


def GetDataFile(filename=""):
    return os.path.abspath(
        os.path.join(os.path.dirname(pytd.__file__), filename))
