#!/usr/bin/env python3
from modbusclient import Payload, AtomicType, Device

import unittest


class DeviceTestCase(unittest.TestCase):

    def setUp(self):
        """Set up test parameters
        """
        self.int = AtomicType("i")
        self.api = [
            Payload(self.int, address=1000, name="Cool Temperature"),
            Payload(self.int, address=1001, name="Hot Temperature"),
            Payload(self.int, address=1002, name="Fancy Voltage 1"),
            Payload(self.int, address=1003, name="Fancy Voltage 2"),
            Payload(self.int, address=1004, name="Average Voltage"),
        ]

    def test_getitem(self):
        device = Device(api=self.api)

        self.assertEqual(device[1000], self.api[0])
        self.assertEqual(device["1001"], self.api[1])
        self.assertEqual(device["Fancy Voltage 1"], self.api[2])
        with self.assertRaises(KeyError):
            x = device[self.api[0]]

    def test_messages(self):
        device = Device(api=self.api)
        self.assertListEqual(list(device.messages("*Voltage*")), self.api[2:])

        self.assertListEqual(list(device.messages("100?")), self.api)

        self.assertListEqual(list(device.messages(1000, "1001")), self.api[:2])


def suite() -> unittest.TestSuite:
    return unittest.TestLoader().loadTestsFromTestCase(DeviceTestCase)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
