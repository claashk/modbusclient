
from asyncio import open_connection
from logging import getLogger
from modbusclient.messages import ApplicationProtocolHeader, REQUEST_TYPES, RESPONSE_TYPES, Error
from modbusclient.functions import ERROR_FLAG
from modbusclient.messages import MODBUS_PROTOCOL_ID, NO_UNIT
from modbusclient.error_codes import MESSAGE_SIZE_ERROR, INVALID_TRANSACTION_ID, UNIT_MISMATCH
from modbusclient.error_codes import NO_ERROR


class Client(object):
    """Modbus client

    Modbus client to send function calls to a server and receive the respective
    responses. Can be used in a with block.

    Arguments:
        host (string): IP Adress of the host. If empty, no connection will be
            attempted. Defaults to the empty string.
        port (int): Port to use. Defaults to 502
        timeout (float): Timeout in seconds. If not set, it will be set to
           the default timeout.
    """
    def __init__(self, host="", port=502, timeout=None):
        self._reader = None
        self._writer = None
        self._host = host
        self._port = port
        self._logger = getLogger('modbus')

    async def __aenter__(self):
        await self.connect()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def is_connected(self):
        """Check if this client is connected to a server

        Return:
            bool: True if and only if this client is connected to a server
        """
        return self._writer is not None and not self._writer.transport.is_closing()

    async def connect(self, host=None, port=None):
        """Connect this client to a host

        Arguments:
            host (string): IP Adress of the host
            port (int): Port to use. Defaults to 502
        """
        self.disconnect()
        if host is not None:
            self._host = host
        if port is not None:
            self._port = port
        self._logger.debug("Connecting to %s:%s ...", self._host, self._port)
        self._reader, self._writer = await open_connection(self._host, self._port)

    def disconnect(self):
        """Disconnect this client

        If this client is connected, the socket will be shutdown and then closed.
        If the client is not connected, calling this method has no effect.
        """
        if self.is_connected():
            self._logger.debug("Disconnecting ...")
            self._writer.close()
            self._reader = None
            # await self._writer.wait_closed() -> python3.7
            self._writer = None

    def request(self, function, data=b"", unit=NO_UNIT, transaction=0, **kwargs):
        """Send a request to the server asynchronously

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
        self._logger.debug("Requesting function %s", str(function))
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
        self._logger.debug("Sending %s request", str(RequestType))
        self._writer.write(buffer)
        return header

    async def get_response(self):
        """Get response from the server

        Return:
            tuple(~modbus.ApplicationProtocolHeader, bytes, int): The following
            values will be returned:
            * The received MBAP header
            * The raw data bytes of the payload without any headers
            * An error code or ``None``, if no error occurred.
        """
        self.assert_connected()
        nbytes = ApplicationProtocolHeader.parser.size
        self._logger.debug("Reading Application Protocol header")
        buffer = await self._reader.readexactly(nbytes)
        header = ApplicationProtocolHeader.from_buffer(buffer)

        if header.protocol != MODBUS_PROTOCOL_ID:
            raise RuntimeError("Invalid protocol ID", header.protocol)

        self._logger.debug("Reading payload")
        buffer = await self._reader.readexactly(header.length - 2)

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
        self._logger.debug("Got response: %s, %s, %s", header, data, err_code)
        return header, data, err_code

    async def iter_responses(self, n):
        """Iter over a number of responses

        Attributes:
            n (int): Number of request headers
        """
        for i in range(n):
            self._logger.debug("Getting response %d of %d", i, n)
            yield await self.get_response()
        return

    async def call(self, function, **kwargs):
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
        resp, data, error = await self.get_response()

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