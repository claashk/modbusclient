from .protocol import NO_UNIT, DEFAULT_PORT
from .error_codes import ModbusError
from .client import Client
from .payload import Payload

from logging import getLogger

logger = getLogger('modbusclient')


def as_payload(msg, api):
    """Lookup message by key
    
    Arguments:
        msg (Payload or key): Either a payload or a 
        api (dict): Api definition
        
    Return:
        ~modbuclient.Payload: Payload instance described by `msg`
    """
    if isinstance(msg, Payload):
        return msg
    return api[msg]


class ApiWrapper(object):
    """Default API implementation to quickly

    Arguments:
        api (dict): Dictionary containing the API definition. Should contain
            a string with desired method name as key and a
            :class:`~modbusclient.payload.Payload` object as value.
        host (str): IP address of the server. Passed verbatim to
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
                 api=dict(),
                 host="",
                 port=DEFAULT_PORT,
                 timeout=None,
                 connect=False,
                 unit=NO_UNIT):
        self._api = api
        self._client = Client(host=host,
                              port=port,
                              timeout=timeout,
                              connect=connect)
        self.unit = unit

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

    def login(self, secret=None):
        """Login using the provided secret.
        
        Shall rise, if login does not succeed.
        
        Raise:
            NotImplementedError:
        """
        raise NotImplementedError()

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
            message (:class:`~modbusclient.payload.Payload` or str): Message
                to read from remote device. If this is not a
                :class:`~modbusclient.payload.Payload` instance, the api
                dictionary will be used with `message` as key to lookup the
                payload.

        Return:
            value: Value of message
        """
        msg = as_payload(message, self._api)
        header, payload, err_code = self._client.call(
            function=msg.reader,
            start=msg.address,
            count=msg.register_count,
            unit=self.unit,
            transaction=0)
        if err_code:
            raise ModbusError(err_code)
        return msg.decode(payload)

    def set(self, message, value):
        """Set value of a single message

        Arguments:
            message (:class:`~modbusclient.payload.Payload`): Message to write to
                remote device. If this is not a
                :class:`~modbusclient.payload.Payload` instance, the api
                dictionary will be used with `message` as key to lookup the
                payload.
            value (object): Value to set for this message.

        Return:
            value: Value of message
        """
        msg = as_payload(message, self._api)
        header, payload, err_code = self._client.call(
            function=msg.writer,
            start=msg.address,
            count=msg.register_count,
            payload=msg.encode(value),
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
        return msg.decode(payload)

    def read(self, selection=None):
        """Save current settings into dictionary

        Arguments:
            selection (iterable): Iterable of messages (API keys or Payload
                objects) to read. If ``None``, all messages of the current API
                are read.

        Return:
            dict: Dictionary containing API message key and setting as value
        """
        retval = dict()
        if selection is None:
            selection = self._api.values()
        for key in selection:
            msg = as_payload(key, self._api)
            if msg.is_readable:
                try:
                    retval[msg] = self.get(msg)
                except Exception as exc:
                    logger.error("While retrieving %s: %s", msg, exc)
        return retval

    def set_from(self, settings):
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
                    retval[msg] = self.set(msg, value)
                except Exception as ex:
                    logger.error("While setting message %s: %s", key, ex)
                except:
                    logger.error("While setting message %s: Unknown error", key)
        return retval
