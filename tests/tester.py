import unittest


class T(unittest.TestCase):
    def eq(self, a, b, m=None): self.assertEqual(a, b, m)
    def neq(self, a, b, m=None): self.assertNotEqual(a, b, m)
    def isType(self, o, cls, m=None): self.assertIsInstance(o, cls, m)
    def notType(self, o, cls, m=None): self.assertNotIsInstance(o, cls, m)
    def notNone(self, o, m=None): self.assertIsNotNone(o, m)
    def isNone(self, o, m=None): self.assertIsNone(o, m)
    def ok(self, x, m=None): self.assertTrue(x, m)
    def notOk(self, x, m=None): self.assertFalse(x, m)
    def hasIn(self, a, b, m=None): self.assertIn(a, b, m)
    def isRef(self, a, b, m=None): self.assertIs(a, b, m)
    def raises(self, exc): return self.assertRaises(exc)
