from datetime import datetime


class Payload(object):
    """Payload parser

    Small wrapper around struct.Struct parser to simplify message definition and
    conversion between binary and python representation

    Arguments:
        format (str): Format string in struct.Struct notation. The leading "!"
           to specify endianess can be omitted
        address (int): Starting address of the message
        mode (str): Permissible read write modes. Defaults to read only ('r')
        name (str): Optional string name
    """
    def __init__(self, dtype, address, name="", mode='r'):
        self._dtype = dtype
        self._address = address
        self._mode = mode
        self._name = name

    def __len__(self):
        """Get length of this message in bytes

        Return:
            int: Number of bytes required by this message
        """
        return len(self._dtype)

    def __str__(self):
        return "Message {} ({})".format(self._address, self._name)

    def __hash__(self):
        """Get hash of this Message

        Return:
            str: equivalent of ``hash(self.address)``

        """
        return hash(self._address)

    def __eq__(self, other):
        """Equality comparison

        Two messages are considered equal, if and only if their addresses match.

        Arguments:
            other (:class:`~sma.Message`): Message to compare to

        Return:
            bool: ``True`` if and only if the addresses of both messages are
            equal.
        """
        return self._address == other._address

    def __ne__(self, other):
        """Inequality comparison

        Arguments:
            other (:class:`~sma.Message`): Message to compare to

        Return:
            bool: ``False`` if and only if the addresses of both messages are
            equal.
        """
        return self._address != other._address

    @property
    def name(self):
        """Get name of this message

        Return:
            str: message name
        """
        return self._name

    @property
    def address(self):
        """Get address (numeric ID) of this message

        Return:
            int: (starting) address of this message
        """
        return self._address

    @property
    def register_count(self):
        """Get number of registers used by this parser

        Return:
            int: Number of 2-byte registers used by this parser
        """
        return (len(self) + 1) // 2

    @property
    def is_writable(self):
        """Check if this message is writable"""
        return 'w' in self._mode

    @property
    def is_write_protected(self):
        """Check if message requires Grid guard code to be written

        Return:
            bool: True if and only if this message is writable exclusively with
                grid guard code
        """
        return "w!" in self._mode

    def encode(self, value):
        """Convert a value to binary modbus representation

        Arguments:
            value (object): Python variable to encode

        Return:
            bytes: Packed binary version of :value:
        """
        return self._dtype.encode(value)

    def decode(self, buffer):
        """Convert bytes from binary modbus representation into variable

        Arguments:
            buffer (bytes): Data in packed binary format

        Return:
            object: Python representation of the data
        """
        return self._dtype.decode(buffer)


class ENUM(Payload):
    """Specialisation for enumeration messages

    Accepts an additional dictionary as argument, which relates the keys to
    a string describing the meaning.

    Arguments:

    """
    def __init__(self, dtype, address, name="", choices=None, mode="r"):
        super().__init__(dtype, address=address, name=name, mode=mode)
        self.choices=choices

    def __getitem__(self, name):
        return self.choices[name]


class FIX(Payload):
    """Specialisation of :class:´~modbus.sma.Message` for fixed point floats

    Arguments:
        dtype ()
    """
    def __init__(self, dtype, address, name="", mode="r", digits=0):
        super().__init__(dtype, address=address, name=name, mode=mode)
        self._scale = 10**digits

    def encode(self, value):
        return super().encode(int(self._scale * value + 0.5))

    def decode(self, bytes):
        val = super().decode(bytes)
        if val is None:
            return None
        return float(val) / self._scale


class DT(Payload):
    """Message for times in seconds since the epoch (1970-01-01)"""
    def encode(self, utc):
        super.encode(int(utc.timestamp() + 0.5))

    def decode(self, buffer):
        sec = super().decode(buffer)
        if sec is None:
            return None
        return datetime.utcfromtimestamp(sec)