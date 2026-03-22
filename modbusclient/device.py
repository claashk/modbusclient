from .protocol import NO_UNIT, DEFAULT_PORT
from .error_codes import ModbusError
from .client import Client
from .payload import Payload
from .api_mixin import ApiMixin

from logging import getLogger
from typing import Any
from collections.abc import Iterable

logger = getLogger('modbusclient')



class Device(ApiMixin):
    """Base class for custom modbus devices

    Args:
        api: Iterable of :class:`~modbusclient.Payload` objects defining the
            device's API
        host: IP address of the device / server. Passed verbatim to
            :class:`~modbusclient.client.Client`
        port: Port of device (server) to connect to. Passed verbatim to
            :class:`~modbusclient.client.Client`
        timeout: Client timeout. Passed verbatim to
            :class:`~modbusclient.client.Client`
        connect: Connect to the device. Defaults to ``False``. Passed
             verbatim to :class:`~modbusclient.client.Client`
        unit: Modbus unit ID of the device. Defaults to NO_UNIT.

    Attributes:
        unit : Modbus unit ID: Defaults to NO_UNIT.
    """
    unit: int

    def __init__(
        self,
        api: Iterable[Payload] | None = None,
        host: str = "",
        port: int = DEFAULT_PORT,
        timeout: int | None = None,
        connect: bool = False,
        unit: int = NO_UNIT
    ) -> None:
        super().__init__(api)
        self._client = Client(host=host,
                              port=port,
                              timeout=timeout,
                              connect=connect)
        self.unit = int(unit)

    def __enter__(self) -> "Device":
        """Context Manager support

        Connects to the server if not already connected.
        """
        self._client.__enter__()
        return self

    def __exit__(self, type, value, traceback) -> None:
        """Context Manager support

        Logs out and disconnects from the server.
        """
        self.logout()
        self.disconnect()

    def is_connected(self) -> bool:
        """Check if this client is connected to a server

        Return:
            ``True`` if and only if this client is connected to a server
        """
        return self._client.is_connected()

    def connect(self, **kwargs: Any) -> None:
        """Connect this client to a host

        Arguments:
            **kwargs: Keyword arguments assed verbatim to
                :meth:`modbusclient.Client.connect`
        """
        self._client.connect(**kwargs)

    def disconnect(self) -> None:
        """Disconnect this client

        If this client is connected, the socket will be shutdown and then closed.
        If the client is not connected, calling this method has no effect.
        """
        self._client.disconnect()

    def login(self, secret: str | None = None) -> None:
        """Login using the provided secret.
        
        Shall rise, if login does not succeed.
        
        Raise:
            NotImplementedError:
        """
        raise NotImplementedError()

    def is_logged_in(self) -> bool:
        """Check if this client is currently logged in

        Intended to be implemented by derived class, if applicable

        Return:
            ``False``.
        """
        return False

    def logout(self) -> None:
        """Log out client

        This is a stub. Intended to be implemented by derived classes.
        """
        return

    def get(self, msg: Payload) -> Any:
        """Get value of a single message

        Args:
            msg: Message to read from remote device

        Return:
            value: Value of message

        Raises:
            ModbusError on communication errors
        """
        header, payload, err_code = self._client.call(
            function=msg.reader,
            start=msg.address,
            count=msg.register_count,
            unit=self.unit,
            transaction=0)
        if err_code:
            raise ModbusError(err_code)
        return msg.decode(payload)

    def set(self, msg: Payload, value: Any) -> Any:
        """Set value of a single message

        Args:
            msg: Message to write to remote device
            value: Value to set for this message.

        Return:
            value: Value actually set
        """
        encoded_payload = msg.encode(value)

        header, payload, err_code = self._client.call(
            function=msg.writer,
            start=msg.address,
            count=msg.register_count,
            payload=encoded_payload,
            unit=self.unit,
            transaction=0)

        if err_code:
            if err_code == 1:
                if not msg.is_writable:
                    raise ModbusError(err_code, "Message is read only")

                if msg.is_write_protected and not self.is_logged_in():
                    self.login()
                    return self.set(msg, value)
            raise ModbusError(err_code)

        if not payload:
            # Some functions do not return the payload. This seems to be the
            # next best thing to do.
            payload = encoded_payload

        return msg.decode(payload)

    def read(
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
                    out[msg] = self.get(msg)
                except Exception as ex:
                    logger.error("While retrieving %s: %s", msg, ex)
        return out

    def write(self, settings: dict[Payload, Any]) -> dict[Payload, Any]:
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
                    out[msg] = self.set(msg, value)
                except Exception as ex:
                    logger.error("While setting %s: %s", msg, ex)
                except:
                    logger.error("While setting %s: Unknown error", msg)
        return out
