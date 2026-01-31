from .functions import *
from .data_types import DataType

from datetime import datetime, timezone

try:
    from typing import override
except ImportError:
    def override(f):
        def inner(*args, **kwargs):
            return f(*args, **kwargs)
        return inner


class Payload:
    """Payload parser

    Small wrapper around parser objects to simplify payload definition. The
    actual parser is passed as argument `dtype` and has to provide

    * a method ``encode`` to encode python objects to bytes
    * a method ``decode`` to convert bytes to python objects
    * a ``__len__`` implementation returning the number of bytes required in the
      encoded string.

    For examples of compatible parser implementations refer to the `data_types`
    module.

    Args:
        dtype: Datatype object capable of converting from python object
            to bytes and back. Must provide methods ``encode`` and ``decode``.
        address: Starting address (register number) of the message
        mode: Permissible read write modes. Defaults to read only (``'r'``)
        reader: Read function as defined in module :mod:`~modbusclient.functions`
            If ``None``, ``READ_HOLDING_REGISTERS`` is assumed if
            ``self.is_writable`` or ``READ_INPUT_REGISTERS`` otherwise.
        writer:
        **kwargs: Additional properties added verbatim to this instance.
    """
    _dtype: DataType
    _address: int
    _mode: str
    _reader: int | None
    _writer: int | None

    def __init__(
        self,
        dtype: DataType,
        address: int,
        mode: str = 'r',
        reader: int | None = None,
        writer: int | None = None,
        **kwargs: dict[str, object]
    ) -> None:
        self._dtype = dtype
        self._address = address
        self._mode = mode
        self._reader = reader
        self._writer = writer
        vars(self).update(kwargs)

        if self._reader is None and self.is_readable:
            if self.is_writable:
                self._reader = READ_HOLDING_REGISTERS
            else:
                self._reader = READ_INPUT_REGISTERS

        if self._writer is None and self.is_writable:
            if self.register_count == 1:
                self._writer = WRITE_SINGLE_REGISTER
            else:
                self._writer = WRITE_MULTIPLE_REGISTERS

    def __len__(self) -> int:
        """Get length of this message in bytes

        Return:
            int: Number of bytes required by this message
        """
        return len(self._dtype)

    @override
    def __str__(self) -> str:
        components = [f"Message {self.address}"]
        for attr, fmt in [("name", " ({})"), ("units", " [{}]")]:
            try:
                components.append(fmt.format(getattr(self, attr)))
            except AttributeError:
                pass
        return "".join(components)

    @override
    def __hash__(self) -> int:
        """Get hash of this Message

        Return:
            str: equivalent of ``hash(self.address)``

        """
        return hash(self._address)

    @override
    def __eq__(self, other: "Payload") -> bool:
        """Equality comparison

        Two messages are considered equal, if and only if their addresses match.

        Args:
            other: Payload to compare to

        Return:
            bool: ``True`` if and only if the addresses of both messages are
            equal.
        """
        return self._address == other._address

    @override
    def __ne__(self, other: "Payload") -> bool:
        """Inequality comparison

        Args:
            other: Payload to compare to

        Return:
            bool: ``False`` if and only if the addresses of both messages are
            equal.
        """
        return self._address != other._address

    @property
    def address(self) -> int:
        """Get address (numeric ID) of this message

        Return:
            (starting) address of this message
        """
        return self._address

    @property
    def register_count(self) -> int:
        """Get number of registers used by this parser

        Return:
            Number of 2-byte registers used by this parser
        """
        return (len(self) + 1) // 2

    @property
    def reader(self) -> int | None:
        """Get function code used to read this value from device

        Return:
            Function code used to read this value from device. ``None`` if
            value cannot be read.
        """
        return self._reader

    @property
    def writer(self) -> int | None:
        """Get function code used to write this value to device

        Return:
            Function code used to write this value to a device. ``None`` if
            value cannot be written.
        """
        return self._writer

    @property
    def is_readable(self) -> bool:
        """Check if this message is readable"""
        return 'r' in self._mode

    @property
    def is_writable(self) -> bool:
        """Check if this message is writable"""
        return 'w' in self._mode

    @property
    def is_write_protected(self) -> bool:
        """Check if message requires some sort of login before write

        Return:
            ``True`` if and only if this message is writable with special
            permissions only.
        """
        return "w!" in self._mode

    def encode(self, value: object) -> bytes:
        """Convert a value to binary modbus representation

        Args:
            value: Python variable to encode

        Return:
            Packed binary version of ``value``.
        """
        return self._dtype.encode(value)

    def decode(self, buffer: bytes) -> object:
        """Convert bytes from binary modbus representation into variable

        Args:
            buffer: Data in packed binary format

        Return:
            Python representation of the data
        """
        return self._dtype.decode(buffer)


class Enum(Payload):
    """Specialisation for enumeration messages

    Accepts an additional dictionary as argument, which maps payload values
    to strings.

    Args:
        dtype: Datatype object capable of converting from python object
            to bytes and back. Must provide methods ``encode`` and ``decode``.
        address: Starting address (register number) of the message
        choices: Dictionary mapping strings to values
        mode: Permissible read write modes. Defaults to read only (``'r'``)
        **kwargs: Additional properties added verbatim to this instance.
    """
    choices: dict[str, object]

    def __init__(
        self,
        dtype: DataType,
        address: int,
        choices: dict[str, object] | None= None,
        mode: str = "r",
        **kwargs: dict[str, object]
    ) -> None:
        super().__init__(dtype, address=address, mode=mode, **kwargs)
        if choices is None:
            self.choices = dict()
        else:
            self.choices= dict(choices)

    def __getitem__(self, name: str) -> object:
        return self.choices[name]


class Fixpoint(Payload):
    """Specialisation of :class:´Payload` for fixed point floats

    Args:
        dtype: Datatype object capable of converting from python object
            to bytes and back. Must provide methods ``encode`` and ``decode``.
        address (int): Starting address (register number) of the message
        mode (str): Permissible read write modes. Defaults to read only (``'r'``)
        digits (int): Number of decimal digits. Defaults to 0.
        **kwargs: Additional properties added verbatim to this instance.
    """
    _scale: int

    def __init__(
        self,
        dtype: DataType,
        address: int,
        mode: str = "r",
        digits: int = 0,
        **kwargs: dict[str, object]
    ) -> None:
        super().__init__(dtype, address=address, mode=mode, **kwargs)
        self._scale = 10**digits

    @override
    def encode(self, value: float) -> bytes:
        return super().encode(int(self._scale * value + 0.5))

    @override
    def decode(self, buffer: bytes) -> float | None:
        val = super().decode(buffer)
        if val is None:
            return None
        return float(val) / self._scale


class Timestamp(Payload):
    """Message for times in seconds since 1970-01-01"""
    def encode(self, utc: datetime) -> bytes:
        return super().encode(int(utc.timestamp()))

    def decode(self, buffer: bytes) -> datetime | None:
        sec = super().decode(buffer)
        if sec is None:
            return None
        return datetime.fromtimestamp(sec, timezone.utc)
