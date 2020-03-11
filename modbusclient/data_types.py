from struct import Struct
import numpy as np


class DataType(object):
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
    def decode(self, bytes):
        val, = super().decode(bytes)

        if val == self._nan:
            return None
        else:
            return val


class String(AtomicType):
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
