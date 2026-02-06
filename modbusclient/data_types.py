from struct import Struct
import numpy as np
from typing import Any

try:
    from typing import override
except ImportError:
    def override(f):
        def inner(*args, **kwargs):
            return f(*args, **kwargs)
        return inner


class DataType:
    """Base class for data type objects

    Base class for objects to be used as parser in combination with
    :class:`~modbusclient.Payload` objects. This base wraps a
    :class:`~struct.Struct` parser for the conversion between python objects and
    binary strings.

    Args:
        format: Format definition as used by :class:`~struct.Struct`. If the
            leading exclamation mark ('!') is omitted, it is added automatically.
            Other byte order marks have to be specified explicitly.
        nan: NAN value to use for this object.
        swap_words: Swap registers (DWORDS) before conversion. This may be
            necessary depending on the memory layout used by the application,
            since MODBUS does not define how to distribute multi-word data types
            over several registers. Defaults to `False`.
    """
    _parser: Struct
    _nan: object | None
    _swap_words: bool

    def __init__(
        self,
        format: str,
        nan: object | None = None,
        swap_words: bool = False
    ) -> None:
        if len(format) > 0 and format[0] in "<>!=":
            fmt = format
        else:
            fmt= "".join(["!", format])
        self._parser = Struct(format=fmt)
        self._nan = nan
        self._swap_words = swap_words

    def __len__(self) -> int:
        """Get length of this message in bytes

        Return:
            Number of bytes required by this message
        """
        return self._parser.size

    def encode(self, *values: object) -> bytes:
        """Encode one or more values into a bytes object

        Args:
            values: Values to encode

        Return:
            Encoded values as bytes object
        """
        retval = self._parser.pack(*values)
        if self._swap_words:
            retval = swap_words(retval)
        return retval

    def decode(self, buffer: bytes) -> tuple[Any, ...]:
        """Convert bytes into a python object represented by this class

        Args:
            buffer: Bytes to decode

        Return:
            Python object defined through the format string
        """
        if self._swap_words:
            buf = swap_words(buffer)
        else:
            buf = buffer
        return self._parser.unpack(buf)
    

class AtomicType(DataType):
    """Wrapper for Atomic datatypes which maps NaN to ``None``

    Identical to :class:`~modbusclient.DataType`, except that NaN will be mapped
    to ``None`` when parsing bytes.
    """
    @override
    def decode(self, buffer: bytes) -> Any | None:
        val, = super().decode(buffer)
        return None if val == self._nan else val


class String(AtomicType):
    """Parser for strings with configurable encoding

    Args:
        len (int): Length of the string in bytes
        encoding (str): Encoding. Defaults to 'utf8'
        swap_words (bool): Defaults to ``False``
    """
    _encoding: str

    def __init__(
        self,
        len: int,
        encoding: str = "utf8",
        swap_words: bool = False
    ) -> None:
        super().__init__(format=f"{len}s", nan=0, swap_words=swap_words)
        self._encoding = str(encoding)

    @override
    def encode(self, value: str) -> bytes:
        return super().encode(value.encode(self._encoding))

    @override
    def decode(self, buffer: bytes) -> str:
        return super().decode(buffer).decode(self._encoding).rstrip("\x00")


def swap_words(arr: bytes) -> bytes:
    """Swap 16-bit words of an array
    
    Args:
        arr: bytes
    
    Return:
        Bytes with pairwise swap of 16-bit words
    """
    return np.flip(np.frombuffer(arr, dtype='i2')).tobytes()


def bcd_decode(byte: int) -> int:
    """Decode BCD encoded byte into number

    Args:
        byte: A single byte

    Return:
        Number as integer
    """
    return 10 * ((0xF0 & byte) >> 4) + (0x0F & byte)


def bcd_encode(number: int) -> int:
    """Decode BCD encoded byte into number

    Args:
        number: A single byte

    Return:
        Number as integer
    """
    if number < 0 or number > 99:
        raise ValueError("Expected a non-negative number < 100", number)
    return ((number // 10) << 4) + number % 10
