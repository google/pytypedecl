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

import sys
from pytypedecl import checker


class FakeReadable(object):
  def Open(self):
    pass

  def Read(self):
    return "Hello"

  def Close(self):
    pass


class NoGoodWritable(object):
  def Open(self):
    pass

  def Write(self):
    pass

  # missing Close


class FakeOpenable(object):
  def Open(self):
    pass


# def ReadStuff(r: ReadInterface) -> str
def ReadStuff(r):
  r.Open()
  result = r.Read()
  r.Close()
  return result


# def GetWritable() -> WriteInterface
def GetWritable():
  return NoGoodWritable()


checker.CheckFromFile(sys.modules[__name__], __file__ + "td")
