#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from modbusclient import Client
import unittest
import unittest.mock as mock


class ClientTestCase(unittest.TestCase):

    def setUp(self):
        """Set up test parameters
        """
        self.ip = "123.234.222.123"
        self.port = "321"
        self.timeout = 12
        self.default_port = 502
        self.default_timeout = None

        patcher = mock.patch("modbusclient.client.socket.create_connection")
        self.socket_patch = patcher.start()
        self.addCleanup(patcher.stop)


    def test_construction(self):
        client = Client()
        self.assertFalse(client.is_connected())
        self.socket_patch.assert_not_called()

        client = Client(self.ip, self.port, self.timeout)
        self.assertTrue(client.is_connected())
        self.socket_patch.assert_called_with((self.ip, self.port), self.timeout)

    def test_context_manager(self):
        with Client(self.ip) as client:
            self.assertTrue(client.is_connected())
            self.socket_patch.assert_called_with((self.ip, self.default_port),
                                                 self.default_timeout)
            sock = client._socket
        sock.shutdown.assert_called_once()
        sock.close.assert_called_once()
        self.assertIsNone(client._socket)
        self.assertFalse(client.is_connected())


def suite():
    return unittest.TestLoader().loadTestsFromTestCase( ClientTestCase )


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run( suite() )
