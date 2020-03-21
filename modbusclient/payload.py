from datetime import datetime
from .functions import *


class Payload(object):
    """Payload parser

    Small wrapper around parser objects to simplify payload definition. The
    actual parser is passed as argument `dtype` and has to provide

    * a method ``encode`` to encode python objects to bytes
    * a method ``decode`` to convert bytes to python objects
    * a ``__len__`` implementation returning the number of bytes required in the
      encoded string.

    For examples of compatible parser implementations refer to the `data_types`
    module.

    Arguments:
        dtype (object): Datatype object capable of converting from python object
            to bytes and back. Must provide methods ``encode`` and ``decode``.
        address (int): Starting address (register number) of the message
        mode (str): Permissible read write modes. Defaults to read only (``'r'``)
        **kwargs (dict): Additional properties added verbatim to this instance.
    """
    def __init__(self,
                 dtype,
                 address,
                 mode='r',
                 reader=None,
                 writer=None,
                 **kwargs):
        self._dtype = dtype
        self._address = address
        self._mode = mode
        self._reader = reader
        self._writer = writer
        vars(self).update(kwargs)

        if self._reader is None:
            if self.is_writable:
                self._reader = READ_HOLDING_REGISTERS
            else:
                self._reader = READ_INPUT_REGISTERS

        if self._writer is None:
            if self.is_writable:
                if self.register_count == 1:
                    self._writer = WRITE_SINGLE_REGISTER
                else:
                    self._writer = WRITE_MULTIPLE_REGISTERS

    def __len__(self):
        """Get length of this message in bytes

        Return:
            int: Number of bytes required by this message
        """
        return len(self._dtype)

    def __str__(self):
        components = ["Message {}".format(self.address)]
        for attr, fmt in [("name", " ({})"), ("units", " [{}]")]:
            try:
                components.append(fmt.format(getattr(self, attr)))
            except AttributeError:
                pass
        return "".join(components)

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
            other (:class:`~modbusclient.Payload`): Payload to compare to

        Return:
            bool: ``True`` if and only if the addresses of both messages are
            equal.
        """
        return self._address == other._address

    def __ne__(self, other):
        """Inequality comparison

        Arguments:
            other (:class:`~modbusclient.Payload`): Payload to compare to

        Return:
            bool: ``False`` if and only if the addresses of both messages are
            equal.
        """
        return self._address != other._address

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
    def reader(self):
        """Get function code used to read this value from device

        Return:
            int: Function code used to read this value from device. ``None`` if
            value cannot be read.
        """
        return self._reader

    @property
    def writer(self):
        """Get function code used to write this value to device

        Return:
            int: Function code used to write this value to a device. ``None`` if
            value cannot be written.
        """
        return self._writer

    @property
    def is_writable(self):
        """Check if this message is writable"""
        return 'w' in self._mode

    @property
    def is_write_protected(self):
        """Check if message requires Grid guard code to be written

        Return:
            bool: True if and only if this message is writable with special
            permissions only.
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


class Enum(Payload):
    """Specialisation for enumeration messages

    Accepts an additional dictionary as argument, which relates the keys to
    a string describing the meaning.

    Arguments:
        choices(dict): Dictionary mapping enum values to values

    """
    def __init__(self, dtype, address, choices=dict(), mode="r", **kwargs):
        super().__init__(dtype, address=address, mode=mode, **kwargs)
        self.choices = choices

    def __getitem__(self, name):
        return self.choices[name]


class Fixpoint(Payload):
    """Specialisation of :class:´Payload` for fixed point floats

    Arguments:
        dtype ()
    """
    def __init__(self, dtype, address, mode="r", digits=0, **kwargs):
        super().__init__(dtype, address=address, mode=mode, **kwargs)
        self._scale = 10**digits

    def encode(self, value):
        return super().encode(int(self._scale * value + 0.5))

    def decode(self, bytes):
        val = super().decode(bytes)
        if val is None:
            return None
        return float(val) / self._scale


class Timestamp(Payload):
    """Message for times in seconds since 1970-01-01"""
    def encode(self, utc):
        super.encode(int(utc.timestamp() + 0.5))

    def decode(self, buffer):
        sec = super().decode(buffer)
        if sec is None:
            return None
        return datetime.utcfromtimestamp(sec)