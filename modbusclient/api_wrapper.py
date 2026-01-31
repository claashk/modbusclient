from .protocol import NO_UNIT, DEFAULT_PORT
from .error_codes import ModbusError
from .client import Client
from .payload import Payload

from logging import getLogger
from typing import Iterable, Any
import re

logger = getLogger('modbusclient')


def iter_matching_names(name:str, api: dict[str, Payload]) -> Iterable[Payload]:
    """Iterate over all payloads matching name pattern

    The ~modbusclient.Payload objects in api must have a ``name`` attribute for
    this to work.

        name: Regular expression pattern for the name. Special characters
            ``'*'`` and ``'?'`` are supported, too.
        api: Api definition

    Yield:
        ~modbusclient.Payload: Payload for each pattern matching `name`
    """
    pattern = re.compile(name.replace("*", ".*").replace("?", "."))
    for m in api.values():
        if pattern.match(m.name):
            yield m


def as_payload(msg: Payload | Any, api, key_type=None):
    """Lookup message by key
    
    Arguments:
        msg (Payload or key): Either a payload or any object convertible to a paylo
        api (dict): Api definition
        key_type (type): Optional key type. If provided, msg is converted to
           key_type before the API lookup is performed. Defaults to ``None``.
        
    Return:
        ~modbusclient.Payload: Payload instance described by `msg`

    Raises:
        KeyError: If msg is not a valid API key.

        ValueError: If msg cannot be converted to the API key_type
    """
    if isinstance(msg, Payload):
        return msg
    if key_type is not None:
        msg = key_type(msg)
    return api[msg]


def iter_payloads(messages, api, key_type=None):
    """Iterate over all payloads defined in various forms

    Arguments:
       messages(Payload, key_type, iterable): Messages to add. If this is a
           :class:`~modbusclient.Payload` object, the object is yielded as a
           single value. If `messages` is convertible `key_type`, the resulting
           key is converted to a :class:`~modbusclient.Payload` objected via the
           `api` before it is yielded. If the above attempts are not successful
           and `messages` is a string, then lookup via :func:`find_names` is
           attempted next and the results are yielded. Otherwise ``messages``
           is interpreted as an iterable and the above matching strategy is
           applied to each of its elements.
        api (dict): Api definition
        key_type (type): Optional key type. If provided, msg is converted to
           key_type before the API lookup is performed. Defaults to ``None``.

    Yield:
        ~modbusclient.Payload: Payload instance described by `msg`
    """
    if not isinstance(messages, (list, tuple)):
        try:
            yield as_payload(messages, api, key_type)
            return
        except ValueError:
            pass

        if isinstance(messages, str):
            yield from iter_matching_names(messages, api)
            return

    for message in messages:
        yield from iter_payloads(message, api=api, key_type=key_type)


def from_cache(selection, cache, api):
    remaining = []
    found = dict()
    for key in selection:
        msg = as_payload(key, api)
        try:
            found[msg] = cache[msg]
        except KeyError:
            remaining.append(msg)
    return found, remaining


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
                 api=None,
                 host="",
                 port=DEFAULT_PORT,
                 timeout=None,
                 connect=False,
                 unit=NO_UNIT):
        self._api = api if api is not None else dict()
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
            **kwargs: Keyword arguments assed verbatim to
                :meth:`modbusclient.Client.connect`
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

    def read(self, selection=None):
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
                    retval[msg] = self.get(msg)
                except Exception as ex:
                    logger.error(f"While retrieving {msg}: {ex}")
        return retval

    def cached_read(self, cache, selection=None):
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
        cached.update(self.read(remaining))
        return cached

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
                    logger.error(f"While setting message {key}: {ex}")
                except:
                    logger.error(f"While setting message {key}: Unknown error")
        return retval
