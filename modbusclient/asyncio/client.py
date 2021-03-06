import asyncio
from logging import getLogger

from ..protocol import ApplicationProtocolHeader, parse_response_body
from ..protocol import new_request, parse_response_header
from ..protocol import UNIT_MISMATCH, NO_UNIT, NO_ERROR, ModbusError

logger = getLogger("modbusclient")


class Client(object):
    """Asynchronous Modbus client

    An asynchronous Modbus client, which can be used in an``async with`` block.

    Arguments:
        host (string): IP Adress of the host. If empty, no connection will be
            attempted. Defaults to the empty string.
        port (int): Port to use. Defaults to 502
        timeout (float): Timeout in seconds. If not set, it will be set to
           the default timeout. Currently not used.
        max_transactions (int): Max. number of transactions send in parallel to
            the server. Defaults to 3.
        max_retries (int): Maximum number of connection retries. Defaults to 5.
            0 disables retries while ``None`` is equivalent to infinite retries.
        loop (EventLoop): If set to ``None``, event loop will be determined by
            the method. Defaults to ``None``. Deprecated from python 3.7 onwards.
    """
    def __init__(self,
                 host="",
                 port=502,
                 timeout=None,
                 max_transactions=3,
                 max_retries=5,
                 loop=None):
        self._reader = None
        self._writer = None
        self._host = host
        self._port = port
        self._max_retries = int(max_retries) if max_retries is not None else None

        # used only because get_running_loop is not available in python < 3.7 and
        # the call to get_event_loop used instead is apparently expensive.
        self._loop = loop

        self._transactions = max_transactions * [(None, None)]
        self._read_lock = asyncio.Lock()

    @property
    def max_transactions(self):
        return len(self._transactions)

    @property
    def loop(self):
        if self._loop is None:
            self._loop = asyncio.get_event_loop()
        return self._loop

    async def __aenter__(self):
        await self.connect()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def is_connected(self):
        """Check if this client is connected to a server

        Return:
            bool: True if and only if this client is connected to a server
        """
        if self._writer is None or self._reader is None:
            return False

        if self._reader.at_eof() or self._writer.transport.is_closing():
            return False

        return True

    async def connect(self, host=None, port=None, max_retries=None):
        """Connect this client to a host

        Arguments:
            host (string): IP Adress of the host
            port (int): Port to use. Defaults to 502
            max_retries (int): Maximum number of retries.
        """
        self.disconnect()
        if host is not None:
            self._host = host
        if port is not None:
            self._port = port
        if max_retries is not None:
            self._max_retries = max_retries

        logger.debug(f"Connecting to {self._host}:{self._port} ...")
        retry = 0
        while True:
            try:
                r, w = await asyncio.open_connection(self._host, self._port)
                self._reader, self._writer = r, w
                return
            except OSError as ex:
                retry += 1
                if self._max_retries is None or retry < self._max_retries:
                    logger.debug(f"Connection failed: {ex}. Retry {retry} of "
                                 f"{self._max_retries}")
                    await asyncio.sleep(0.5)
                else:
                    raise

    def disconnect(self):
        """Disconnect this client

        If this client is connected, the socket will be shutdown and then closed.
        If the client is not connected, calling this method has no effect.
        """
        if self.is_connected():
            logger.debug("Disconnecting ...")
            #cancel all existing future
            for i, (header, future) in enumerate(self._transactions):
                if future is not None:
                    logger.debug("Cancelled future for Transaction ID {} ..."
                                 .format(header.transaction))
                    future.cancel()
                    self._transactions[i] = (None, None)

            self._writer.close()
            self._reader = None
            # await self._writer.wait_closed() -> python3.7
            self._writer = None

    async def request(self,
                      function,
                      payload=b"",
                      unit=NO_UNIT,
                      transaction=None,
                      **kwargs):
        """Send a request to the server

        Awaits transaction ID `transaction` to become available. Then creates
        a request and sends it to the server. A future for the reply is created
        and added to ``self._transactions[transaction]``.

        Note that the future will not be completed unless
        :meth:`Client.get_response` is called. For a wrapper which makes sure
        the result is collected, see :meth:`Client.call`

        Arguments:
            function (int): Function code
            payload (bytes): Data sent along with the request. Empty by default.
                Used only for writing functions.
            unit (int): Unit ID of device. Defaults to NO_UNIT
            transaction (int): Transaction ID. If set to ``None``, a transaction
                ID will be generated by :meth:`Client.get_transaction_id`.
                Defaults to ``None``.
            **kwargs: Keyword arguments passed verbatim to the request of the
                function

        Return:
            tuple(~modbusclient.ApplicationProtocolHeader, asyncio.Future):

            * Request header
            * Future yielding response header, payload and error code

        Raise:
            ValueError: If transaction ID is out of bounds
        """
        logger.debug("Requesting function %s", str(function))
        await self.assert_connected()
        if transaction is None:
            transaction = await self.get_transaction_id()
        elif transaction < 0 or transaction >= self.max_transactions:
            raise ValueError("Invalid transaction ID", transaction)

        while self._transactions[transaction][1] is not None:
            logger.debug("Awaiting completion of transaction %d ...",
                         transaction)
            await self._transactions[transaction][1]

        header, msg = new_request(function=function,
                                  payload=payload,
                                  unit=unit,
                                  transaction=transaction,
                                  **kwargs)
        future = self.loop.create_future()
        try:
            self._writer.write(msg)
            logger.debug("Sent request with transaction ID %d.", transaction)
            await self._writer.drain()
        except Exception as exc:
            logger.warning(f"Error sending request with transaction ID "
                           f"{transaction}: {exc}")
            future.set_exception(exc)
        self._transactions[transaction] = (header, future)
        return header, future

    async def get_response(self):
        """Get response from the server

        Locks the internal reader lock and reads the next message on the input
        stream. If the transaction ID is valid and a matching future is found,
        the result of the future will be set

        Return:
            tuple(~modbusclient.ApplicationProtocolHeader, bytes, int): The
            following values are returned:

            * The received MBAP header
            * The raw data bytes of the payload without any headers
            * An error code or ``None``, if no error occurred.
        """
        await self.assert_connected()
        logger.debug("Awaiting response ...")
        nbytes = ApplicationProtocolHeader.parser.size
        try:
            # Lock to make sure header and body are read in sequence
            async with self._read_lock:
                buffer = await self._reader.readexactly(nbytes)
                header = parse_response_header(buffer)
                buffer = await self._reader.readexactly(header.length - 2)
        except asyncio.IncompleteReadError:
            logger.warning("Connection closed unexpectedly. Cleaning up ...")
            self.disconnect()
            return

        payload, err_code = parse_response_body(header, buffer)
        logger.debug(f"Got response: {header}, {payload}, {err_code}")

        try:
            req, future = self._transactions[header.transaction]
            self._transactions[header.transaction] = (None, None)
        except IndexError:
            raise ModbusError(f"Got unknown transaction ID {header.transaction}")

        assert(header.transaction == req.transaction)

        if future is not None and not future.cancelled():
            if err_code == NO_ERROR:
                if header.unit == req.unit or header.unit == NO_UNIT:
                    future.set_result((header, payload, err_code))
                else:
                    future.set_exception(ModbusError(UNIT_MISMATCH))
            else:
                future.set_exception(ModbusError(err_code))
        else:
            logger.error("Future for transaction %d already complete",
                         header.transaction)
        return

    async def call(self, function, **kwargs):
        """Call a function on the server and await the result

        Sends a request via :meth:`Client.request` and processes responses until
        the resulting future is complete.

        Arguments:
            function (int): Function code
            **kwargs: Keyword arguments passed verbatim to
                :meth:`~Client.request`.

        Return:
            tuple(~modbusclient.ApplicationProtocolHeader, bytes, int): The
            following values will be returned:

            * The received MBAP header
            * The raw data bytes of the payload without any headers
            * An error code or ``None``, if no error occurred.

        Raise:
            :class:`~modbusclient.protocol.ModbusError`: On modbus related errors

            :class:`asyncio.CancelledError`: If future has been cancelled
        """
        header, future = await self.request(function, **kwargs)
        while not future.done():
            await self.get_response()
        return future.result()  # will raise, if an exception is set

    async def assert_connected(self):
        """Assert client is connected

        A helper method which raises an exception, if the client is not connected

        Raise:
            RuntimeError: if :meth:`~modbus.Client.is_connected` returns
            ``False``.
        """
        logger.debug("Checking connection status ...")
        if not self.is_connected():
            await self.connect()

    async def get_transaction_id(self):
        """Get transaction ID

        Checks whether any of the available transaction IDs is available and
        returns the first available ID. If no ID is available,
        :meth:`Client.get_response` is invoked, until a free ID is found.

        Return:
            int: Available transaction ID in the range
            ``[0:self.max_transactions]``.
        """
        logger.debug("Generating transaction ID ..."),
        while True:
            for i, (header, future) in enumerate(self._transactions):
                if future is None:
                    return i
            logger.debug(f"Max. transactions ({self.max_transactions}) active")
            await self.get_response()
