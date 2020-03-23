from autobahn.asyncio.component import Component


class ComponentBase(object):
    """A base class for WAMP components

    This class provides a template to turn an asynchronous Modbus client into a
    WAMP client using the Autobahn package. Provided you have an API client
    derived from  :class:`modbusclient.asyncio.ApiWrapper`, you can use this
    class as base class for your WAMP client and provice the API client
    as `client` argument. This avoids the repetition of some boiler plate code.

    Arguments:
        transports (list or str): Passed verbatim to
            :class:`autobahn.asyncio.component.Component` as `transports`.
        realm (str): WAMP realm. Passed verbatim to
            :class:`autobahn.asyncio.component.Component` as `realm`.
        client (:class:`modbusclient.asyncio.ApiWrapper`): An implementation of
            an API wrapper.

    Attributes:
        component (:class:`autobahn.asyncio.component.Component`): Autobahn
            WAMP component wrapped by this class
        session (:class:`autobahn.wamp.protocol.ApplicationSession`): Session
            passed during on_join. ``None`` if client has not joined any session.
    """
    def __init__(self, transports, realm, client):
        self._component = Component(transports=transports, realm=realm)
        self._client = client
        self._component.on('join', self._join)
        self._component.on('leave', self._leave)

        self._session = None

    @property
    def component(self):
        """Get component wrapped by this instance

        Return:
            :class:`autobahn.asyncio.component.Component`: Autobahn
            WAMP component wrapped by this class
        """
        return self._component

    @property
    def session(self):
        """Get currently joined session

        Return:
            :class:`autobahn.wamp.protocol.ApplicationSession`: Session passed
                during on_join. ``None`` if client is currently not joined to
                any session.
        """
        return self._session

    async def _join(self, session, details):
        """Call back invoked when joining (on_join)

        Sets the internal session member variable and prints an info message.

        Arguments:
            session (:class:`autobahn.wamp.protocol.ApplicationSession`):
                Application session.
            details (dict): Dictionary with details.
        """
        self._session = session
        self.info('Joined session {session}: {details}',
                  session=session, details=details)

    async def _leave(self, session, reason):
        self.info("Disconnecting from session {session}. Reason: {reason}",
                  session=session, reason=reason)
        self._session = None

    def debug(self, msg, **kwargs):
        """Create debug level log message

        Arguments:
            msg (str): Log message.
            **kwargs: Keyword arguments passed to message formatter
        """
        self._component.log.debug(msg, **kwargs)

    def info(self, msg, **kwargs):
        """Create info level log message

        Arguments:
            msg (str): Log message.
            **kwargs: Keyword arguments passed to message formatter
        """
        self._component.log.info(msg, **kwargs)

    def warning(self, msg, **kwargs):
        """Create warning level log message

        Arguments:
            msg (str): Log message.
            **kwargs: Keyword arguments passed to message formatter
        """
        self._component.log.warning(msg, **kwargs)

    def error(self, msg, **kwargs):
        """Create error level log message

        Arguments:
            msg (str): Log message.
            **kwargs: Keyword arguments passed to message formatter
        """
        self._component.log.error(msg, **kwargs)
