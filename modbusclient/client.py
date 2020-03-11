
import socket

from .protocol import ApplicationProtocolHeader, NO_UNIT
from .protocol import new_request, parse_response_header, parse_response_body
from .protocol import INVALID_TRANSACTION_ID, UNIT_MISMATCH


class Client(object):
    """Modbus client

    Modbus client to send function calls to a server and receive the respective
    responses. Can be used in a with block.

    Arguments:
        address (string): IP Adress of the host. If empty, no connection will be
            attempted. Defaults to the empty string.
        port (int): Port to use. Defaults to 502
        timeout (float): Timeout in seconds. If not set, it will be set to
           the default timeout.
    """
    def __init__(self, address="", port=502, timeout=None):
        self._socket = None

        if address:
            self.connect(address, port, timeout)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.disconnect()

    def is_connected(self):
        """Check if this client is connected to a server

        Return:
            bool: True if and only if this client is connected to a server
        """
        return bool(self._socket)

    def connect(self, address, port=502, timeout=None):
        """Connect this client to a host

        Arguments:
            address (string): IP Adress of the host
            port (int): Port to use. Defaults to 502
            timeout (float): Timeout in seconds. If not set, it will be set to
               the default timeout.
        """
        self.disconnect()
        self._socket = socket.create_connection((address, port), timeout)

    def disconnect(self):
        """Disconnect this client

        If this client is connected, the socket will be shutdown and then closed.
        If the client is not connected, calling this method has no effect.
        """
        if self.is_connected():
            self._socket.shutdown(socket.SHUT_RDWR)
            self._socket.close()
            self._socket = None

    def request(self, function, payload=b"", unit=NO_UNIT, transaction=0, **kwargs):
        """Send a request to the server

        Arguments:
            function (int): Function code
            payload (bytes): Data sent along with the request. Empty by default.
                Used only for writing functions.
            unit (int): Unit ID of device. Defaults to NO_UNIT
            transaction (int): Transaction ID. Defaults to 0.
            kwargs (dict): Keyword arguments passed verbatim to the request of
              the function

        Return:
            ~modbus.ApplicationProtocolHeader: Header of the request
        """
        self.assert_connected()
        header, msg = new_request(function=function,
                                  payload=payload,
                                  unit=unit,
                                  transaction=transaction,
                                  **kwargs)
        self._socket.sendall(msg)
        return header

    def receive(self, size):
        """Receive a given number of bytes from the server

        Arguments:
            size (int): Number of bytes to receive

        Return:
            bytes: Buffer containing the received bytes.

        Raises:
            ConnectionAbortedError: If the connection is terminated unexpectedly
        """
        self.assert_connected()
        bytes_read = 0
        chunks = []
        while bytes_read < size:
            chunk = self._socket.recv(min(size - bytes_read, 512))
            if not chunk:
                raise ConnectionAbortedError("Connection terminated unexpectedly")
            bytes_read += len(chunk)
            chunks.append(chunk)
        return b"".join(chunks)

    def get_response(self):
        """Get response from the server

        Return:
            tuple(~modbusclient.ApplicationProtocolHeader, bytes, int): The
            following values will be returned:
            * The received MBAP header
            * The raw data bytes of the payload without any headers
            * An error code or ``None``, if no error occurred.
        """
        buffer = self.receive(ApplicationProtocolHeader.parser.size)
        header = parse_response_header(buffer)
        buffer = self.receive(header.length - 2)
        payload, err_code = parse_response_body(header, buffer)

        return header, payload, err_code

    def iter_responses(self, n):
        """Iter over a number of responses

        Attributes:
            n (int): Number of request headers
        """
        for i in range(n):
            yield self.get_response()
        return

    def call(self, function, **kwargs):
        """Call a function on the server and return the result

        Sends a request via :meth:`~modbus.Client.request` followed by an
        immediate call of :meth:`~modbus.Client.get_response`

        Arguments:
            function (int): Function code
            **kwargs (dict): Keyword arguments passed verbatim to
                :meth:`~modbus.Client.request`

        Return:
            tuple: Data returned by :meth:`~modbus.Client.get_response`
        """
        req = self.request(function, **kwargs)
        resp, data, error = self.get_response()

        if resp.transaction != req.transaction:
            error = INVALID_TRANSACTION_ID

        if resp.unit != req.unit:
            if resp.unit != NO_UNIT:
                error = UNIT_MISMATCH

        return resp, data, error

    def assert_connected(self):
        """Assert client is connected

        A helper method which raises an exception, if the client is not connected

        Raise:
            RuntimeError: if :meth:`~modbus.Client.is_connected` returns
            ``False``.

        """
        if not self.is_connected():
            raise RuntimeError("Client is not connected. Call connect first")