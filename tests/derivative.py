#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from modbusclient import Derivative
import unittest
from datetime import datetime, timedelta


class DerivativeTestCase(unittest.TestCase):

    def setUp(self):
        """Set up test parameters
        """
        self.diff = Derivative()

    def test_derivative(self):
        t0, now = (self.diff.now(), datetime.utcnow())
        dt = (now - datetime.fromtimestamp(t0)).total_seconds()
        self.assertGreaterEqual(dt, 0.)
        self.assertLess(dt, 0.001)

        self.assertIsNone(self.diff.last_timestamp)
        self.assertIsNone(self.diff.last_value)
        self.assertIsNone(self.diff(2., t0))

        t1 = datetime.fromtimestamp(t0) + timedelta(seconds=0.5)
        self.assertAlmostEqual(2., self.diff(3., t1.timestamp()))

        self.assertIsNone(self.diff(4, t1.timestamp()))
        self.assertEqual(self.diff.last_timestamp, t1.timestamp())
        self.assertEqual(self.diff.last_value, 4.)
        self.assertTrue(isinstance(self.diff.last_timestamp, float))

        t0 = self.diff.now()
        self.diff(5.)
        t1 = self.diff.now()

        self.assertGreaterEqual(self.diff.last_timestamp, t0)
        self.assertGreaterEqual(t1, self.diff.last_timestamp)
        self.assertEqual(self.diff.last_value, 5.)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(DerivativeTestCase)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run( suite() )
