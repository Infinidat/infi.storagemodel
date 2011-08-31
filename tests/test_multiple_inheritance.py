
from unittest import TestCase

#http://www.python.org/download/releases/2.3/mro/

class A(object):
    def method(self):
        return 'A'

class B(object):
    def method(self):
        return 'B'

class Case1(A, B):
    pass

class C(A):
    def method(self):
        return "C"

class Case2(C, B):
    pass

class D(A):
    pass

class Case3(D, B):
    pass

class Case3A(B, D):
    pass

class E(B):
    pass

class Case4(E, D):
    pass

class A1(object):
    def __init__(self, arg1):
        pass

class A2(object):
    def __init__(self, arg1, arg2):
        pass

class Case5(A1, A2):
    def __init__(self, arg1, arg2):
        A1.__init__(self, arg1)
        A2.__init__(self, arg1, arg2)

class MultipleInheritanceTestCase(TestCase):
    def test__case_1(self):
        obj = Case1()
        self.assertEqual(obj.method(), 'A')

    def test__case_2(self):
        obj = Case2()
        self.assertEqual(obj.method(), 'C')

    def test__case_3(self):
        obj = Case3()
        self.assertEqual(obj.method(), 'A')

    def test__case_3a(self):
        obj = Case3A()
        self.assertEqual(obj.method(), 'B')

    def test__case_4(self):
        obj = Case4()
        self.assertEqual(obj.method(), 'B')

    def test__case_5(self):
        obj = Case5(1, 2)
