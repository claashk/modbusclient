
import re
from collections.abc import Iterable

from .payload import Payload


class ApiMixin:
    """Mixes in API related functionality

    Implements API related functionality used by both synchronous and
    asynchronous device implementations.

    Uses the address (as string) and (if available) the name attribute of each
    payload as key. The payload itself is stored as value. Note that the same
    payload may thus exist twice in the returned dictionary.

    Args:
        api: Iterable of :class:`~modbusclient.Payload` objects defining the
            device's API
        keys: Tuple of attributes by which payloads are indexed. Defaults
            to ``('address', 'name')``. Empty attributes are not indexed.
    """
    _api: dict[str, Payload]

    def __init__(
        self,
        api: Iterable[Payload] | None = None,
        keys: tuple[str, ...] = ("address", "name")
    ) -> None:
        self._api = dict()
        if api is None:
            return

        for msg in api:
            for attr in keys:
                k = str(getattr(msg, attr, ""))
                if k:
                    self._api[k] = msg

    def __getitem__(self, msg: str | int) -> Payload:
        """Access payload by message address or message name

        Args:
            msg: Message address or message name

        Return:
            Payload instance
        """
        return self._api[str(msg)]

    @property
    def api(self) -> set[Payload]:
        """Get API of this device

        Return:
            Iterable of Payload objects in current API
        """
        return set(self._api.values())

    def messages(self, pattern: str | int, *args: str | int) -> Iterable[Payload]:
        """Iterate over all payloads matching a given pattern

        Args:
            pattern: Regular expression pattern for the name. Special characters
                ``'*'`` and ``'?'`` are supported, too. If this is an integer,
                it is interpreted as message address.
            *args: Additional patterns.

        Yields:
            Payload with keys matching any of the provided arguments. Duplicates
            are removed.
        """
        if not args:
            try:
                yield self[pattern]
                return
            except KeyError:
                pass

        out: set[Payload] = set()
        for p in [pattern, *args]:
            _pattern = re.compile(str(p).replace("*", ".*").replace("?", "."))
            out |= {v for k, v in self._api.items() if _pattern.match(k)}

        yield from out
