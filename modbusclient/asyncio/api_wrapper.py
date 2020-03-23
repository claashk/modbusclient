from ..protocol import NO_UNIT, DEFAULT_PORT, ModbusError, ILLEGAL_FUNCTION_ERROR
from ..payload import Payload
from .client import Client

from logging import getLogger

logger = getLogger('modbusclient')


class ApiWrapper(object):
    """Asynchronous API implementation

    Arguments:
        api (dict): Dictionary containing the API definition. Should contain
            a string with desired method name as key and a
            :class:`~modbusclient.payload.Payload` object as value.
        host (str): IP address of the server. Passed verbatim to
            :class:`~modbusclient.asyncio.client.Client`
        port (int): Port to connect to at the server. Passed verbatim to
            :class:`~modbusclient.asyncio.client.Client`
        timeout (int): Client timeout. Passed verbatim to
            :class:`~modbusclient.asyncio.client.Client`
        max_transactions (int): Maximum number of parallel transactions. Passed
            verbatim to :class:`~modbusclient.asyncio.client.Client`.
        unit (int): Modbus unit ID to use. Defaults to NO_UNIT.

    Attributes:
        unit (int): Modbus unit ID: Defaults to NO_UNIT.
    """
    def __init__(self,
                 api=dict(),
                 host="",
                 port=DEFAULT_PORT,
                 timeout=None,
                 max_transactions=3,
                 unit=NO_UNIT):
        self._api = api
        self._client = Client(host=host,
                              port=port,
                              timeout=timeout,
                              max_transactions=max_transactions)
        self.unit = unit

    async def __aenter__(self):
        """Context Manager support

        Connects to the server if not already connected.
        """
        await self._client.__aenter__()
        return self

    async def __aexit__(self, type, value, traceback):
        """Context Manager support

        Logs out and disconnects from the server.
        """
        self.logout()
        self.disconnect()

    def is_connected(self):
        """Check if this client is connected to a server

        Return:
            bool: True if and only if this client is connected to a server
        """
        return self._client.is_connected()

    async def connect(self, **kwargs):
        """Connect this client to a host

        Arguments:
            address (string): IP Adress of the host
            port (int): Port to use. Defaults to 502
            timeout (float): Timeout in seconds. If not set, it will be set to
               the default timeout.
        """
        await self._client.connect(**kwargs)

    def disconnect(self):
        """Disconnect this client

        If this client is connected, the socket will be shutdown and then closed.
        If the client is not connected, calling this method has no effect.
        """
        self._client.disconnect()

    def is_logged_in(self):
        """Check if this client is currently logged in

        Intended to be implemented by derived class, if applicable

        Return:
            bool: False.
        """
        return False

    def logout(self):
        """Log out client

        This is a stub. Intended to be implemented by derived classes.
        """
        return

    async def get(self, message):
        """Get value of a single message

        Arguments:
            message (:class:`~modbusclient.payload.Payload` or str): Message to
                read from remote device. If this is not a
                :class:`~modbusclient.payload.Payload` instance, the api
                dictionary will be used with `message` as key to lookup the
                payload.

        Return:
            value: Value of message
        """
        if not isinstance(message, Payload):
            message = self._api[message]

        header, payload, err_code = await self._client.call(
            function=message.reader,
            start=message.address,
            count=message.register_count,
            unit=self.unit)

        return message.decode(payload)

    async def set(self, message, value):
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
        if not isinstance(message, Payload):
            message = self._api[message]

        try:
            header, payload, err_code = await self._client.call(
                function=message.writer,
                start=message.address,
                count=message.register_count,
                payload=message.encode(value),
                unit=self.unit)
        except ModbusError as ex:
            err_code = ex.args[0]
            if err_code == ILLEGAL_FUNCTION_ERROR:
                if not message.is_writable:
                    raise ModbusError(err_code, "Message is read only")

                if message.is_write_protected and not self.is_logged_in():
                    raise ModbusError(err_code,
                                      "Login required to modify this message")
            raise
        return header

    async def save(self, selection=None):
        """Save current settings into dictionary

        Arguments:
            selection (iterable): Iterable of messages (API keys) to save. If
                ``None``, all messages of the current API are backed up.

        Return:
            dict: Dictionary containing API message key and setting as value
        """
        retval = dict()
        if selection is None:
            selection = self._api.keys()
        for msg in selection:
            try:
                retval[msg] = await self.get(msg)
            except Exception as exc:
                logger.error("While retrieving '%s': %s", msg, exc)
        return retval

    async def load(self, settings):
        """Load settings from dictionary

        Arguments:
            settings (dict): Dictionary with settings as returned by
                 :meth:`~Client.save`
        Return:
            list: Successfully modified settings
        """
        retval = []
        for key, value in settings.items():
            msg = self._api[key]
            if msg.is_writable:
                try:
                    await self.set(msg, value)
                    retval.append(msg)
                except Exception as ex:
                    logger.error("While setting message %s: %s", key, ex)
                except:
                    logger.error("While setting message %s: Unknown error", key)
        return retval
