from ..protocol import NO_UNIT, DEFAULT_PORT, ModbusError, ILLEGAL_FUNCTION_ERROR
from ..api_wrapper import as_payload, from_cache
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
                 api=None,
                 host="",
                 port=DEFAULT_PORT,
                 timeout=None,
                 max_transactions=3,
                 unit=NO_UNIT):
        self._api = api if api is not None else dict()
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
        await self.logout()
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

    async def login(self, secret=None):
        """Login using the provided secret
        
        Has to be implemented by derived class. Shall raise an exception
        if login was not successfull.
        
        Arguments:
            secret (object): Optional secret.
        """
        raise NotImplementedError("login")

    def is_logged_in(self):
        """Check if this client is currently logged in

        Intended to be implemented by derived class, if applicable

        Return:
            bool: False.
        """
        return False

    async def logout(self):
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
        msg = as_payload(message, self._api)
        logger.debug("Retrieving {} ...".format(msg))
        header, payload, err_code = await self._client.call(
            function=msg.reader,
            start=msg.address,
            count=msg.register_count,
            unit=self.unit)
        return msg.decode(payload)

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
        msg = as_payload(message, self._api)
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

    async def read(self, selection=None):
        """Save current settings into dictionary

        Arguments:
            selection (iterable): Iterable of messages (API keys or Payload
                objects) to read. If ``None``, all messages of the current API
                are read.

        Return:
            dict: Dictionary containing Payload as key and setting as value
        """
        retval = dict()
        if selection is None:
            selection = self._api.values()
        for key in selection:
            msg = as_payload(key, self._api)
            if msg.is_readable:
                try:
                    retval[msg] = await self.get(msg)
                except Exception as exc:
                    logger.error("While retrieving '%s': %s", msg, exc)
        return retval

    async def cached_read(self, cache, selection=None):
        """Read values from device, which are not found in cache

        Arguments:
            cache (dict): Cache with Payload instance as key
            selection (iterable): Iterable of messages (API keys or Payload
                objects) to read. If ``None``, all messages of the current API
                are read.
        Return:
            dict: Dictionary containing Payload as key and setting as value
        """
        if selection is None:
            selection = self._api.values()
        cached, remaining = from_cache(selection=selection,
                                       cache=cache,
                                       api=self._api)
        update = await self.read(remaining)
        cached.update(update)
        return cached

    async def set_from(self, settings):
        """Load settings from dictionary

        Arguments:
            settings (dict): Dictionary with settings as returned by
                 :meth:`Client.read`
        Return:
            dict: Successfully modified settings with their respective value
        """
        retval = dict()
        for key, value in settings.items():
            msg = as_payload(key, self._api)
            if msg.is_writable:
                try:
                    retval[msg] = await self.set(msg, value)
                except Exception as ex:
                    logger.error("While setting message %s: %s", key, ex)
                except:
                    logger.error("While setting message %s: Unknown error", key)
        return retval
