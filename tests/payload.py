#!/usr/bin/env python3

from datetime import datetime, timezone, timedelta
from modbusclient import Payload, AtomicType, Timestamp
from modbusclient.protocol import READ_INPUT_REGISTERS

import numpy as np
from typing import Any

import unittest


class PayloadTestCase(unittest.TestCase):

    def setUp(self) -> None:
        """Set up test parameters
        """
        self.float = AtomicType("f")
        self.int = AtomicType("i")
        self.short = AtomicType("H")
        self.long = AtomicType("l")

    def new(
        self,
        dtype: AtomicType | None = None,
        address: int = 1000,
        **kwargs: dict[str, Any]
    ) -> Payload:
        if dtype is None:
            dtype = self.int
        return Payload(dtype, address, **kwargs)

    def test_construction(self):
        p1 = self.new(self.float)
        self.assertEqual(p1.address, 1000)
        self.assertEqual(len(p1), p1._dtype._parser.size)
        self.assertEqual(p1.reader, READ_INPUT_REGISTERS)
        self.assertEqual(p1.register_count, 2)
        self.assertRaises(AttributeError, getattr, p1, "name")
        self.assertFalse(p1.is_writable)
        self.assertFalse(p1.is_write_protected)

        p2 = self.new(address=2000, mode='rw', name="power", units="kW")
        self.assertEqual(p2.name, "power")
        self.assertEqual(p2.units, "kW")
        self.assertTrue(p2.is_writable)
        self.assertFalse(p2.is_write_protected)

        p3 = self.new(address=2000, mode='rw!')
        self.assertTrue(p3.is_writable)
        self.assertTrue(p3.is_write_protected)

    def test_str(self):
        self.assertEqual(str(self.new()), "Message 1000")
        self.assertEqual(str(self.new(name="name")), "Message 1000 (name)")
        self.assertEqual(str(self.new(units="kW")), "Message 1000 [kW]")
        self.assertEqual(str(self.new(name="power", units="W")),
                         "Message 1000 (power) [W]")

    def test_encode(self):
        p1 = self.new()
        for val in [0, 10, 100, -123, -555]:
            self.assertEqual(p1.decode(p1.encode(val)), val)

        buf = np.array([0., 10., 1.234e-15, -123e13, -555.45678], dtype=np.float32)
        p2 = self.new(dtype=self.float)
        for val in buf:
            self.assertEqual(p2.decode(val.tobytes()[::-1]), val)

    def test_hash_and_comparisons(self):
        p1 = self.new()
        p2 = self.new(address=1234)
        p3 = self.new(address=1243)
        p4 = self.new(dtype=self.float, address=1000, name="something")

        self.assertEqual(hash(p1), hash(1000))
        self.assertEqual(hash(p2), hash(1234))
        self.assertEqual(hash(p3), hash(1243))
        self.assertEqual(hash(p4), hash(1000))

        self.assertFalse(p1 == p2)
        self.assertFalse(p1 == p3)
        self.assertFalse(p2 == p3)
        self.assertTrue(p1 == p4)

        self.assertTrue(p1 != p2)
        self.assertTrue(p1 != p3)
        self.assertTrue(p2 != p3)
        self.assertFalse(p1 != p4)

    def test_timestamp(self) -> None:
        p = Timestamp(dtype=self.long, address=666, mode="r", units="seconds")
        t = datetime.now(tz=timezone.utc)
        tout = p.decode(p.encode(t))

        t0 = datetime(1970, 1, 1).astimezone(timezone.utc)
        dt = int((t - t0) / timedelta(seconds=1))

        self.assertEqual(tout, t0 + timedelta(seconds=dt))


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(PayloadTestCase)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
