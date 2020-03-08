
import socket
from .messages import ApplicationProtocolHeader, REQUEST_TYPES, RESPONSE_TYPES, Error
from .functions import ERROR_FLAG
from .messages import MODBUS_PROTOCOL_ID, NO_UNIT
from .error_codes import MESSAGE_SIZE_ERROR, INVALID_TRANSACTION_ID, UNIT_MISMATCH
from .error_codes import NO_ERROR


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

    def request(self, function, data=b"", unit=NO_UNIT, transaction=0, **kwargs):
        """Send a request to the server

        Arguments:
            function (int): Function code
            data (bytes): Data sent along with the request. Empty by default.
                Used only for writing functions.
            unit (int): Unit ID of device. Defaults to NO_UNIT
            transaction (int): Transaction ID. Defaults to 0.
            kwargs (dict): Keyword arguments passed verbatim to the request of
              the function

        Return:
            ~modbus.ApplicationProtocolHeader: Header of the request
        """
        self.assert_connected()
        try:
            RequestType = REQUEST_TYPES[function]
        except KeyError:
            raise RuntimeError("Unsupported Function ID", function)
        if data:
            kwargs['size'] = len(data)
        request = RequestType(**kwargs)
        header = ApplicationProtocolHeader(transaction=transaction,
                                           protocol=MODBUS_PROTOCOL_ID,
                                           length=2+len(request),
                                           unit=unit,
                                           function=function)
        buffer = b"".join([header.to_buffer(), request.to_buffer(), data])
        self._socket.sendall(buffer)
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
            tuple(~modbus.ApplicationProtocolHeader, bytes, int): The following
            values will be returned:
            * The received MBAP header
            * The raw data bytes of the payload without any headers
            * An error code or ``None``, if no error occurred.
        """
        buffer = self.receive(ApplicationProtocolHeader.parser.size)
        header = ApplicationProtocolHeader.from_buffer(buffer)

        if header.protocol != MODBUS_PROTOCOL_ID:
            raise RuntimeError("Invalid protocol ID", header.protocol)

        buffer = self.receive(header.length - 2)

        if header.function > ERROR_FLAG: #second byte = function code
            msg = Error.from_buffer(buffer)
            err_code = msg.exception_code
            data = b""
        else:
            response_type = RESPONSE_TYPES[header.function]
            msg = response_type.from_buffer(buffer)
            data = buffer[len(msg):]

            if data and (len(data) != msg.size):
                err_code = MESSAGE_SIZE_ERROR
            else:
                err_code = NO_ERROR
        return header, data, err_code

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