from .protocol import NO_UNIT, DEFAULT_PORT
from .error_codes import ModbusError
from .client import Client


class DefaultApi(object):
    """Default API implementation to quickly

    Arguments:
        commands (dict): Dictionary containing the API definition. Should contain
            a string with desired method name as key and a
            :class:`~modbusclient.payload.Payload` object as value.
        address (str): IP address of the server. Passed verbatim to
            :class:`~modbusclient.client.Client`
        port (int): Port to connect to at the server. Passed verbatim to
            :class:`~modbusclient.client.Client`
        timeout (int): Client timeout. Passed verbatim to
            :class:`~modbusclient.client.Client`
        connect (bool): Connect to the client. Defaults to `False`. Passed
             verbatim to :class:`~modbusclient.client.Client`

    Attributes:
        unit (int): Modbus unit ID: Defaults to NO_UNIT.
    """
    def __init__(self,
                 commands,
                 address="",
                 port=DEFAULT_PORT,
                 timeout=None,
                 connect=False,
                 unit=NO_UNIT):
        self.__dict__['_api'] = commands
        self.__dict__['_client'] = Client(address, port, timeout, connect=connect)
        self.__dict__['unit'] = unit

    def __enter__(self):
        """Context Manager support

        Connects to the server if not already connected.
        """
        self._client.__enter__()
        return self

    def __exit__(self, type, value, traceback):
        """Context Manager support

        Logs out and disconnects from the server.
        """
        self.logout()
        self.disconnect()

    def __getattr__(self, item):
        """Get value of a single message

        Return:
            value: Value of message
        """
        return self.get(self._api[item])

    def __setattr__(self, key, value):
        """Set value of a single message

        Return:
            value: Value of message
        """
        self.set(self._api[key], value)

    def is_connected(self):
        """Check if this client is connected to a server

        Return:
            bool: True if and only if this client is connected to a server
        """
        return self._client.is_connected()

    def connect(self, **kwargs):
        """Connect this client to a host

        Arguments:
            address (string): IP Adress of the host
            port (int): Port to use. Defaults to 502
            timeout (float): Timeout in seconds. If not set, it will be set to
               the default timeout.
        """
        self._client.connect(**kwargs)

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

    def get(self, message):
        """Get value of a single message

        Arguments:
            message (:class:`~modbusclient.payload.Payload`): Message (payload)
                to read from remote device

        Return:
            value: Value of message
        """
        header, payload, err_code = self._client.call(
            function=message.reader,
            start=message.address,
            count=message.register_count,
            unit=self.unit,
            transaction=0)
        if err_code:
            raise ModbusError(err_code)
        return message.decode(payload)

    def set(self, message, value):
        """Set value of a single message

        Arguments:
            message (:class:`~modbusclient.payload.Payload`): Message (payload)
                to write to remote device
            value (object): Value to set for this message.

        Return:
            value: Value of message
        """
        header, payload, err_code = self._client.call(
            function=message.writer,
            start=message.address,
            count=message.register_count,
            payload=message.encode(value),
            unit=self.unit,
            transaction=0)

        if err_code:
            if err_code == 1:
                if not message.is_writable:
                    raise ModbusError(err_code, "Message is read only")

                if message.is_write_protected and not self.is_logged_in():
                    raise ModbusError(err_code,
                                      "Login required to modify this message")
            raise ModbusError(err_code)
        return header

    def save(self, selection=None):
        """Save current settings into dictionary

        Arguments:
            selection (iterable): Iterable of messages to save. If None, all
                messages are backed up

        Return:
            dict: Dictionary containing message as key and setting as value
        """
        if selection is None:
            return
        retval = dict()
        for msg in selection:
            retval[msg] = self.get(msg)
        return retval

    def load(self, settings):
        """Load settings from dictionary

        Arguments:
            settings (dict): Dictionary with settings as returned by
                 :meth:`~sma.Client.save`
        Return:
            list: Successfully modified settings
        """
        retval = []
        for msg, value in settings.items():
            if msg.is_writable:
                try:
                    self.set(msg, value)
                    retval.append(msg)
                except:
                    pass
        return retval