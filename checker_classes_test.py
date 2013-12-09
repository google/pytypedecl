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


import unittest
from pytypedecl import checker
from pytypedecl.parse import typing
from tests import classes


class TestCheckerClasses(unittest.TestCase):

  def testEmailer(self):
    emailer = classes.Emailer()
    page_email = "nobody@example.com"
    expected_msg = "sending email to " + page_email
    self.assertEquals(expected_msg, emailer.SendEmail(page_email))

    with self.assertRaises(checker.CheckTypeAnnotationError) as context:
      emailer.MakeAnnoucement("nobody@example.com")

    expected = checker.ParamTypeErrorMsg("MakeAnnoucement",
                                         "emails",
                                         str,
                                         typing.GenericType1(list, str))

    [actual] = context.exception.args[0]
    self.assertEquals(expected, actual)

    with self.assertRaises(checker.CheckTypeAnnotationError) as context:
      classes.Emailer.GetServerInfo("25")

    expected = checker.ParamTypeErrorMsg("GetServerInfo",
                                         "port",
                                         str,
                                         int)

    [actual] = context.exception.args[0]
    self.assertEquals(expected, actual)

  def testUtils(self):
    utils = classes.Utils()
    self.assertEquals("aaa", utils.Repeat("a", 3.0))

    with self.assertRaises(checker.CheckTypeAnnotationError) as context:
      utils.Repeat("a", "3")

    expected = checker.OverloadingTypeErrorMsg("Repeat")

    [actual] = context.exception.args[0]
    self.assertEquals(expected, actual)

  def testComparators(self):

    self.assertEquals(True, classes.Comparators.IsGreater(20, 10))

    # call using with class name
    with self.assertRaises(checker.CheckTypeAnnotationError) as context:
      classes.Comparators.IsGreater("20", 10)

    expected = checker.ParamTypeErrorMsg("IsGreater",
                                         "a",
                                         str,
                                         int)

    [actual] = context.exception.args[0]
    self.assertEquals(expected, actual)

    # call using instance of comparators
    comparators = classes.Comparators()
    with self.assertRaises(checker.CheckTypeAnnotationError) as context:
      comparators.IsGreater(20, "10")

    expected = checker.ParamTypeErrorMsg("IsGreater",
                                         "b",
                                         str,
                                         int)

    [actual] = context.exception.args[0]
    self.assertEquals(expected, actual)


if __name__ == "__main__":
  unittest.main()
