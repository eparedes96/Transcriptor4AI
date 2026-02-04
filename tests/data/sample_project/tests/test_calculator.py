import unittest

from data.sample_project.src.calculator import Calculator


class TestCalculator(unittest.TestCase):
    def test_addition(self):
        calc = Calculator()
        result = calc.add(5)
        self.assertEqual(result, 5)

def test_standalone_pytest():
    assert 1 + 1 == 2