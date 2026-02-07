from collections.abc import Generator
import socket

from .protocol import ApplicationProtocolHeader, NO_UNIT, DEFAULT_PORT
from .protocol import new_request, parse_response_header, parse_response_body
from .error_codes import INVALID_TRANSACTION_ID, UNIT_MISMATCH


class Client:
    """Synchronous Modbus client

    Sends function calls to a server and receives the respective responses.
    Supports the context manager protocol.

    Args:
        host: IP Address of the host. If empty, no connection will be attempted.
            Defaults to the empty string.
        port: Port to use. Defaults to ``502``.
        timeout: Timeout in seconds. If ``None``, the default timeout will be
            used. Defaults to ``None``.
        connect: If ``True``, the client immediately connects to the given host.
            A call to :meth:`connect` or :meth:`__enter__` is required otherwise.

    Attributes:
        host (string): IP Address of the host
        port (int): Port to use. Defaults to 502
        timeout (int or None): Timeout in seconds
    """
    def __init__(
            self,
            host: str = "",
            port: int = DEFAULT_PORT,
            timeout: float | None = None,
            connect: bool = True
        ) -> None:
        self._socket = None

        self.host: str = host
        self.port: int = port
        self.timeout: float | None = timeout

        if self.host and connect:
            self.connect()

    def __enter__(self) -> "Client":
        if not self.is_connected():
            self.connect()
        return self

    def __exit__(self, type, value, traceback) -> None:
        self.disconnect()

    def is_connected(self) -> bool:
        """Check if this client is connected to a server

        Return:
            ``True`` if and only if this client is connected to a server
        """
        return bool(self._socket)

    def connect(self, **kwargs)-> None:
        """Connect this client to a host

        Args:
            host: IP Address of the host. If provided, it will replace
                the current :attr:`Client.address`. Defaults to
                :attr:`Client.address`
            port: Port to use. If provided, it will replace
                the current :attr:`Client.port`. Defaults to :attr:`Client.port`.
            timeout (float): Timeout in seconds. If provided, it will replace
                the current :attr:`Client.timeout`. Defaults to
                :attr:`Client.timeout`
        """
        self.disconnect()
        self.host = kwargs.get("host", self.host)
        self.port = kwargs.get("port", self.port)
        self.timeout = kwargs.get("timeout", self.timeout)
        self._socket = socket.create_connection(
            (self.host, self.port),
            self.timeout
        )

    def disconnect(self) -> None:
        """Disconnect from host

        If this client is connected, the socket will be shutdown and then closed.
        If the client is not connected, calling this method has no effect.
        """
        if self.is_connected():
            self._socket.shutdown(socket.SHUT_RDWR)
            self._socket.close()
            self._socket = None

    def request(
            self,
            function: int,
            payload: bytes = b"",
            unit: int = NO_UNIT,
            transaction: int = 0,
            **kwargs
    ) -> ApplicationProtocolHeader:
        """Send a request to the server

        Args:
            function: Function code
            payload: Data sent along with the request. Used only for writing
                functions. Empty by default.
            unit: Unit ID of device. Defaults to ``NO_UNIT``.
            transaction: Transaction ID. Defaults to 0.
            **kwargs: Keyword arguments passed verbatim to the request of
              the function

        Return:
            Header of the request
        """
        self.assert_connected()
        header, msg = new_request(function=function,
                                  payload=payload,
                                  unit=unit,
                                  transaction=transaction,
                                  **kwargs)
        self._socket.sendall(msg)
        return header

    def receive(self, size: int) -> bytes:
        """Receive a given number of bytes from the server

        Args:
            size: Number of bytes to receive

        Return:
            Buffer containing the received bytes.

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

    def get_response(self)-> tuple[ApplicationProtocolHeader, bytes, int | None]:
        """Get response from the server

        Return:

            * The received MBAP header
            * The raw data bytes of the payload without any headers
            * An error code or ``None``, if no error occurred.
        """
        buffer = self.receive(ApplicationProtocolHeader.parser.size)
        header = parse_response_header(buffer)
        buffer = self.receive(header.length - 2)
        payload, err_code = parse_response_body(header, buffer)

        return header, payload, err_code

    def iter_responses(self, n: int) -> Generator[tuple[ApplicationProtocolHeader, bytes, int | None]]:
        """Iterate over a number of responses

        Attrs:
            n: Number of request headers
        """
        for i in range(n):
            yield self.get_response()
        return

    def call(
            self,
            function: int,
            **kwargs
    ) -> tuple[ApplicationProtocolHeader, bytes, int | None]:
        """Call a function on the server and return the result

        Sends a request via :meth:`~modbus.Client.request` followed by an
        immediate call of :meth:`~modbus.Client.get_response`

        Args:
            function: Function code
            **kwargs: Keyword arguments passed verbatim to
                :meth:`~modbus.Client.request`

        Return:
            Data returned by :meth:`~modbus.Client.get_response`
        """
        req = self.request(function, **kwargs)
        resp, data, error = self.get_response()

        if resp.transaction != req.transaction:
            error = INVALID_TRANSACTION_ID

        if resp.unit != req.unit:
            if resp.unit != NO_UNIT:
                error = UNIT_MISMATCH

        return resp, data, error

    def assert_connected(self) -> None:
        """Assert client is connected

        A helper method which raises an exception, if the client is not connected

        Raise:
            RuntimeError: if :meth:`~modbus.Client.is_connected` returns
            ``False``.

        """
        if not self.is_connected():
            raise RuntimeError("Client is not connected. Call connect first")
