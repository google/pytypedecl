"""Tests for parse.utils."""



class UtilsTest(googletest.TestCase):

  def testGetBuiltins(self):
    builtins = utils.GetBuiltins()
    self.assertIsNotNone(builtins)
    self.assertTrue(hasattr(builtins, "modules"))


if __name__ == '__main__':
  googletest.main()
