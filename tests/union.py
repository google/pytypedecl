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


"""Used for tests."""

# pylint: disable=unused-argument
# pylint: disable=unused-import
# pylint: disable=g-line-too-long

import sys
from pytypedecl import checker
# some signatures use type defined in the simple module
from tests import simple


# def StrToInt(i :str?) -> int
def StrToInt(i):
  if i is None:
    return 0
  return int(i)


# def Add(a: int?, b: int?) -> int?
# def Add(a: float?, b: float?) -> float?
def Add(a, b):
  if a is None or b is None:
    return None
  return a + b


# def AddToFloat(a: int | float, b: int | float) -> float
def IntOrFloat(a, b):
  return 42.0


# def IntOrNone(a : int | None) -> int | None
def IntOrNone(a):
  return a


# def AppleOrBananaOrOrange(f : simple.Apple | simple.Banana | simple.Orange) -> None
def AppleOrBananaOrOrange(f):
  return None


class Readable(object):

  def Read(self):
    pass


class Writable(object):

  def Write(self):
    pass


# def DoSomeIOStuff(f : Readable & Writable) -> str
def DoSomeIOStuff(f):
  return "cool"


# def UnionReturn() -> list | tuple
def UnionReturn():
  return [42]


# def UnionReturnError() -> int | list
def UnionReturnError():
  return 42,


class File(Readable, Writable):
  pass


checker.CheckFromFile(sys.modules[__name__], __file__ + "td")
