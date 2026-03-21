from autobahn.asyncio.component import Component
from autobahn.wamp.protocol import ApplicationSession
from .api_wrapper import ApiWrapper

class ComponentBase:
    """A base class for WAMP components

    This class provides a template to turn an asynchronous Modbus client into a
    WAMP client using the Autobahn package. Provided you have an API client
    derived from  :class:`modbusclient.asyncio.ApiWrapper`, you can use this
    class as base class for your WAMP client and provide the API client
    as `client` argument. This avoids the repetition of some boiler plate code.

    Args:
        transports: Passed verbatim to
            :class:`autobahn.asyncio.component.Component` as `transports`.
        realm: WAMP realm. Passed verbatim to
            :class:`autobahn.asyncio.component.Component` as `realm`.
        client: API wrapper implementation.
    """
    def __init__(
        self,
        transports: list[str] | str,
        realm: str,
        client: ApiWrapper
    ) -> None:
        self._component: Component = Component(transports=transports, realm=realm)
        self._client: ApiWrapper = client
        self._component.on('join', self._join)
        self._component.on('leave', self._leave)

        self._session: ApplicationSession | None = None

    @property
    def component(self) -> Component:
        """Access component wrapped by this instance

        Return:
            Autobahn WAMP component wrapped by this class
        """
        return self._component

    @property
    def session(self)-> ApplicationSession | None:
        """Access currently joined session

        Return:
            Session passed during ``on_join``. ``None`` if client is currently
            not joined to any session.
        """
        return self._session

    async def _join(
        self,
        session: ApplicationSession,
        details: dict[str, str]
    ) -> None:
        """Call back invoked when joining (on_join)

        Sets the internal session member variable and prints an info message.

        Args:
            session: Application session.
            details: Dictionary with details.
        """
        self._session = session
        self.info(f'Joined session {session}: {details}')

    async def _leave(
        self,
        session: ApplicationSession,
        reason: dict[str, str]
    ) -> None:
        """Call back invoked when leaving (on_leave)

        Args:
            session: Application session.
            details: Dictionary with details.
        """
        self.info(f"Disconnecting from session {session}. Reason: {reason}")
        self._session = None

    def debug(self, msg: str, **kwargs) -> None:
        """Create debug level log message

        Args:
            msg: Log message.
            **kwargs: Keyword arguments passed to message formatter
        """
        self._component.log.debug(msg, **kwargs)

    def info(self, msg: str, **kwargs) -> None:
        """Create info level log message

        Args:
            msg: Log message.
            **kwargs: Keyword arguments passed to message formatter
        """
        self._component.log.info(msg, **kwargs)

    def warning(self, msg: str, **kwargs) -> None:
        """Create warning level log message

        Args:
            msg: Log message.
            **kwargs: Keyword arguments passed to message formatter
        """
        self._component.log.warning(msg, **kwargs)

    def error(self, msg: str, **kwargs) -> None:
        """Create error level log message

        Args:
            msg: Log message.
            **kwargs: Keyword arguments passed to message formatter
        """
        self._component.log.error(msg, **kwargs)
