from ..protocol import NO_UNIT, DEFAULT_PORT
from ..error_codes import ModbusError, ILLEGAL_FUNCTION_ERROR
from .client import Client
from ..payload import Payload
from ..api_mixin import ApiMixin

from logging import getLogger
from typing import Any
from collections.abc import Iterable

logger = getLogger('modbusclient')


class Device(ApiMixin):
    """Asynchronous base class for custom modbus devices

    Args:
        api: Iterable of :class:`~modbusclient.Payload` objects defining the
            device's API
        host: IP address of the device / server. Passed verbatim to
            :class:`~modbusclient.asyncio.client.Client`
        port: Port of device (server) to connect to. Passed verbatim to
            :class:`~modbusclient.asyncio.client.Client`
        timeout: Client timeout. Currently, ignored.
        max_transactions: Maximum number of concurrent transactions. Passed
            verbatim to :class:`~modbusclient.asyncio.client.Client`.
            Defaults to ``3``.
        unit: Modbus unit ID of the device. Defaults to ``NO_UNIT``.

    Attributes:
        unit : Modbus unit ID.
    """
    unit: int
    _client: Client

    def __init__(
        self,
        api: Iterable[Payload] | None = None,
        host: str = "",
        port: int = DEFAULT_PORT,
        timeout: int | None = None,
        max_transactions: int = 3,
        unit: int = NO_UNIT
    ) -> None:
        super().__init__(api)
        self._client = Client(host=host,
                              port=port,
                              timeout=timeout,
                              max_transactions=max_transactions)
        self.unit = unit

    async def __aenter__(self) -> "Device":
        """Context Manager support

        Connects to the server if not already connected.
        """
        await self._client.__aenter__()
        return self

    async def __aexit__(self, type, value, traceback) -> None:
        """Context Manager support

        Logs out and disconnects from the server.
        """
        await self.logout()
        self.disconnect()

    def is_connected(self) -> bool:
        """Check if this client is connected to a server

        Return:
            ``True`` if and only if this client is connected to a server
        """
        return self._client.is_connected()

    async def connect(self, **kwargs):
        """Connect this client to a host

        Args:
            address (string): IP Address of the host
            port (int): Port to use. Defaults to 502
            timeout (float): Timeout in seconds. If not set, it will be set to
               the default timeout.
        """
        await self._client.connect(**kwargs)

    def disconnect(self) -> None:
        """Disconnect this client

        If this client is connected, the socket will be shutdown and then closed.
        If the client is not connected, calling this method has no effect.
        """
        self._client.disconnect()

    async def login(self, secret: str | None = None) -> None:
        """Login using the provided secret
        
        Has to be implemented by derived class. Shall raise an exception
        if login was not successful.
        
        Args:
            secret: Optional secret.
        """
        raise NotImplementedError("login")

    def is_logged_in(self) -> bool:
        """Check if this client is currently logged in

        Intended to be implemented by derived class, if applicable

        Return:
            ``False``.
        """
        return False

    async def logout(self) -> None:
        """Log out client

        This is a stub. Intended to be implemented by derived classes.
        """
        return

    async def get(self, msg: Payload) -> Any:
        """Get value of a single message

        Args:
            msg: Message to read from remote device

        Return:
            value: Value of message

        Raises:
            ModbusError on communication errors
        """
        logger.debug("Retrieving %s ...", msg)
        header, payload, err_code = await self._client.call(
            function=msg.reader,
            start=msg.address,
            count=msg.register_count,
            unit=self.unit)  # raises an exception on error
        return msg.decode(payload)

    async def set(self, msg: Payload, value: Any) -> Any:
        """Set value of a single message

        Arguments:
            message (:class:`~modbusclient.payload.Payload` or str): Message
                to write to remote device. If this is not a
                :class:`~modbusclient.payload.Payload` instance, the api
                dictionary will be used with `message` as key to lookup the
                payload.
            value (object): Value to set for this message.

        Return:
            value: Value of message
        """
        encoded_payload = msg.encode(value)

        try:
            header, payload, err_code = await self._client.call(
                function=msg.writer,
                start=msg.address,
                count=msg.register_count,
                payload=encoded_payload,
                unit=self.unit)
        except ModbusError as ex:
            err_code = ex.args[0]
            if err_code == ILLEGAL_FUNCTION_ERROR:
                if not msg.is_writable:
                    raise ModbusError(err_code, "Message is read only")

                if message.is_write_protected and not self.is_logged_in():
                    await self.login() # Shall rise, if unsuccessful
                    return await self.set(msg, value)
            raise

        if not payload:
            # Some functions do not return the payload. This seems to be the
            # next best thing to do.
            payload = encoded_payload

        return msg.decode(payload)

    async def read(
        self,
        messages: Iterable[Payload] | None = None,
        cache: dict[Payload, Any] | None = None
    ) -> dict[Payload, Any]:
        """Read several messages into a dictionary

        Args:
            messages: Messages to read (specified either by address or by
                name). If ``None``, all known messages are read. Defaults to
                ``None``.
            cache: Dictionary of cached messages. If not ``None``, messages found
                in cache are copied from the cache and are not read from device.
                Defaults to ``None``.

        Return:
            Dictionary containing Payload as key and associated setting as value
        """
        out = dict() if cache is None else cache.copy()
        _messages = self.api if messages is None else set(messages)
        _messages = _messages - out.keys()

        for msg in _messages:
            if msg.is_readable:
                try:
                    out[msg] = await self.get(msg)
                except Exception as exc:
                    logger.error("While retrieving '%s': %s", msg, exc)
        return out

    async def write(self, settings: dict[Payload, Any]) -> dict[Payload, Any]:
        """Write device settings from dictionary

        Args:
            settings: Dictionary with settings as returned by :meth:`Device.read`

        Return:
            Successfully modified settings with their respective value
        """
        out = dict()
        known_messages = self.api
        for msg, value in settings.items():
            if msg in known_messages and msg.is_writable:
                try:
                    out[msg] = await self.set(msg, value)
                except Exception as ex:
                    logger.error("While setting message %s: %s", msg, ex)
                except:
                    logger.error("While setting message %s: Unknown error", msg)
        return out
