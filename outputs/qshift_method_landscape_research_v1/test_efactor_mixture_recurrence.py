"""Algebraic tests for the fixed-prior one-change e-mixture recurrence."""
from fractions import Fraction
import unittest


class MixtureRecurrenceTests(unittest.TestCase):
    def test_exact_recurrence_matches_direct_component_sum(self):
        sequences = [
            [Fraction(9,10), Fraction(6,5), Fraction(7,10), Fraction(11,10)],
            [Fraction(1), Fraction(1), Fraction(1), Fraction(1)],
            [Fraction(3,2), Fraction(2,3), Fraction(5,4), Fraction(4,5), Fraction(7,6)],
        ]
        for factors in sequences:
            a = Fraction(0)
            for t, ell in enumerate(factors, start=1):
                a = ell * (a + Fraction(1, t * (t + 1)))
                direct = Fraction(1, t + 1)
                for s in range(1, t + 1):
                    product = Fraction(1)
                    for i in range(s - 1, t):
                        product *= factors[i]
                    direct += Fraction(1, s * (s + 1)) * product
                self.assertEqual(a + Fraction(1, t + 1), direct)

    def test_prior_and_supermartingale_mass_identity(self):
        for t in range(1, 10001):
            w_t = Fraction(1, t * (t + 1))
            future_mass = Fraction(1, t + 1)
            previous_future_mass = Fraction(1, t)
            self.assertEqual(w_t + future_mass, previous_future_mass)
        self.assertEqual(sum((Fraction(1, s * (s + 1)) for s in range(1, 10001)), Fraction()), Fraction(10000, 10001))


if __name__ == '__main__':
    unittest.main()
