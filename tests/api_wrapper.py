#!/usr/bin/env python3
from modbusclient import Payload, AtomicType
from modbusclient import as_payload, iter_payloads

import unittest


class ApiWrapperTestCase(unittest.TestCase):

    def setUp(self):
        """Set up test parameters
        """
        self.int = AtomicType("i")
        self.msg = [
            self.new(address=1000, name="Cool Temperature"),
            self.new(address=1001, name="Hot Temperature"),
            self.new(address=1002, name="Fancy Voltage 1"),
            self.new(address=1003, name="Fancy Voltage 2"),
            self.new(address=1004, name="Average Voltage"),
        ]
        self.api = {m.address: m for m in self.msg}

    def new(self, address=1000, dtype=None, **kwargs):
        if dtype is None:
            dtype = self.int
        return Payload(dtype, address, **kwargs)

    def test_as_payload(self):
        self.assertEqual(as_payload(self.msg[0], self.api), self.msg[0])
        self.assertEqual(as_payload(1001, self.api), self.msg[1])
        self.assertRaises(KeyError, as_payload, "1002", self.api)
        self.assertEqual(as_payload("1002", self.api, key_type=int), self.msg[2])
        self.assertRaises(ValueError, as_payload, "1002a", self.api, int)

    def test_iter_payloads(self):
        self.assertListEqual(list(iter_payloads(self.msg[0], self.api)),
                             self.msg[0:1])
        self.assertListEqual(list(iter_payloads(1002, self.api)),
                             self.msg[2:3])
        self.assertListEqual(list(iter_payloads("*Voltage ?", self.api, int)),
                             self.msg[2:4])

        msg = ["*Voltage*", "*Temperature"]
        self.assertSetEqual(set(iter_payloads(msg, self.api, int)),
                            set(self.msg))


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ApiWrapperTestCase)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run( suite() )
