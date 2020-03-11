from struct import Struct
import numpy as np


class DataType(object):
    """Base class for data type objects

    Base class for objects to be used as parser in combination with
    :class:`~modbusclient.Payload` objects. This base wraps a
    :class:`~struct.Struct` parser for the conversion between python objects and
    binary strings.

    Arguments:
        format (str): Format definition as used by :class:`~struct.Struct`. If
        the leading exclamation mark ('!') is omitted, it is added automatically.
        Other byte order marks have to be specified explicitly.
        nan (object): NAN value to use for this object.
        swap_words (bool): Swap registers (DWORDS) before conversion. This may
        be necessary depending on the memory layout used by the application,
        since MODBUS does not define, how multi-word data types are distributed
        over various registers. Defaults to `False`.
    """
    def __init__(self, format, nan=None, swap_words=False):
        if len(format) > 0 and format[0] in "<>!=":
            fmt = format
        else:
            fmt= "".join(["!", format])
        self._parser = Struct(format=fmt)
        self._nan = nan
        self._swap_words = swap_words

    def __len__(self):
        """Get length of this message in bytes

        Return:
            int: Number of bytes required by this message
        """
        return self._parser.size

    def encode(self, *values):
        retval = self._parser.pack(*values)
        if self._swap_words:
            retval = swap_words(retval)
        return retval

    def decode(self, bytes):
        if self._swap_words:
            buf = swap_words(bytes)
        else:
            buf = bytes
        return self._parser.unpack(buf)
    

class AtomicType(DataType):
    """A wrapper for Atomic datatypes which maps NaN to None

    Identical to :class:`~modbusclient.DataType`, except that NaN will be mapped
    to ``None`` when parsing bytes.
    """
    def decode(self, bytes):
        val, = super().decode(bytes)

        if val == self._nan:
            return None
        else:
            return val


class String(AtomicType):
    """Parser for strings with configurable encoding

    Arguments:
        len (int): Length of the string in bytes
        encoding (str): Encoding. Defaults to 'utf8'
        swap_words (bool): Defaults to ``False``
    """
    def __init__(self, len, encoding="utf8", swap_words=False):
        super().__init__("{}s".format(len), nan=0, swap_words=swap_words)
        self._encoding = encoding

    def encode(self, value):
        return super().encode(value.encode(self._encoding))

    def decode(self, bytes):
        return super().decode(bytes).decode(self._encoding)


def swap_words(arr):
    """Swap 16-bit words of an array
    
    Arguments:
        arr (bytes): bytes
    
    Return:
        bytes: Bytes with pairwise swap of 16-bit words
    """
    return np.flip(np.frombuffer(arr, dtype='i2')).tobytes()


def bcd_decode(byte):
    """Decode BCD encoded byte into number

    Arguments:
        byte (int): A single byte

    Return:
        int: Number as integer
    """
    return 10 * ((0xF0 & byte) >> 4) + (0x0F & byte)


def bcd_encode(number):
    """Decode BCD encoded byte into number

    Arguments:
        byte (int): A single byte

    Return:
        int: Number as integer
    """
    if number < 0 or number > 99:
        raise ValueError("Expected a non-negative number < 100", number)

    return ((number // 10) << 4) + number % 10
