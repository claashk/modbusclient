
from collections import namedtuple
try:
    from collections.abc import Buffer
except ImportError:
    Buffer = bytes

from typing import NamedTuple
from struct import Struct
import logging

from .error_codes import (
    NO_ERROR,
    MESSAGE_SIZE_ERROR
)

from .functions import (
    ERROR_FLAG,
    READ_HOLDING_REGISTERS,
    READ_INPUT_REGISTERS,
    WRITE_MULTIPLE_REGISTERS,
    WRITE_SINGLE_REGISTER
)

logger = logging.getLogger('modbusclient')


MODBUS_PROTOCOL_ID = 0
NO_UNIT = 0xFF
DEFAULT_PORT = 502


def __create_header(
    name: str,
    format: str,
    attrs: str,
    defaults: tuple[object, ...] | None = None
) -> type[NamedTuple]:
    """Helper function used to create various header types

    Creates a header class derived from namedtuple. The namedtuple attributes
    are used to store the header data. Classes returned by this function contain
    the following additional methods
    * static method ``from_buffer`` creates a class instance from a binary buffer
    * ``to_buffer`` writes the header to a binary buffer
    * ``__len__`` returns the length of the header (excluding payload) in bytes

    Args:
        name: Name of class to create
        format: Format string recognized by python's Struct
        attrs: Attributes to add. Format as expected by namedtuple
        defaults: Default values for the attribute in ``attrs``

    Return:
        class: Class object capable of storing the header content with additional
        methods to parse and serialize the stored data in binary form.
    """
    Base = namedtuple("Base", attrs)

    def new(cls, *args, **kwargs) -> Base:
        """Create a new class object

        Ars:
            cls (class): Passed verbatim to Base.__new__
            *args (*args): Positional arguments passed verbatim to Base
            **kwargs (dict): Keyword arguments passed verbatim to Base.__new__
        """
        return Base.__new__(cls, *args, **kwargs)

    @classmethod
    def from_buffer(cls, buffer: Buffer, offset: int=0):
        """Create message from buffer

        Invokes the parser on a buffer an returns the class created from the
        data extracted from the buffer

        Args:
            cls: Class to create
            buffer (iterable): Buffer containing packed binary data
            offset (int): Number of bytes to skip at the begin of buffer. Defaults
                to zero.

        Return:
            class: Class instance created from binary data
        """
        return cls(*cls.parser.unpack_from(buffer, offset))

    def to_buffer(self):
        """Write current message to buffer in packed binary form

        Invokes the internal parser to create a bytes object representing the
        current instance in packed binary form

        Return:
            bytes: String containing current instance in packed binary form
        """
        return self.parser.pack(*self)

    def __len__(self):
        """Get length of current message in bytes

        Return:
            int: Length of current message in packed binary form
        """
        return self.parser.size

    msg_type = type(name,
                           (Base, ),
                           dict(format=format,
                                parser= Struct("!" + format),
                                from_buffer=from_buffer,
                                to_buffer=to_buffer,
                                __new__=new,
                                __len__=__len__))
    if defaults:
        msg_type.__new__.__defaults__ = tuple(defaults)
    return msg_type


ApplicationProtocolHeader = __create_header(
    name="ApplicationProtocolHeader",
    format="3H2B",
    attrs="transaction protocol length unit function",
    defaults=(1, 0, 0, 3, 0x80)
)
ApplicationProtocolHeader.__doc__ = """Modbus Application Protocol Header (MBAP)

The application header in this implementation has a size of eight bytes. It is
added to every request sent by a client. The server copies the MBAP into its
response with a modified length field.

Attrs:
    transaction (int): Transaction ID to uniquely identify the transaction if
        several requests are sent in parallel
    protocol (int): MODBUS protocol id (always 0)
    length (int) Number of bytes including the unit identifier byte and all
       following data bytes. For a request, this has to be set by the client,
       while the response length is set by the server
    unit (int): Unit ID of the server. Defaults to NO_UNIT
    function (int): Function code. Assumes the error function code (0x80) if an
        error is encountered. In the MODBUS specification this is part of the
        PDU, but in order to simplify the communication, we include it into the
        MBAP here. 
"""

ReadRequest = __create_header(
    name="ReadRequest",
    format="2H",
    attrs="start count"
)
ReadRequest.__doc__ = """Modbus Read Request Protocol Data Unit (PDU)

Attrs:
    start (int): Address of (first) register to read
    count (int): Number of coils/registers to read

Note:
    A PDU usually starts with a single byte containing the function code, which
    is part of the :class:`~modbusclient.ApplicationProtocolHeader` in this
    implementation.
"""

WriteRequest = __create_header(
    name="WriteRequest",
    format="2HB",
    attrs="start count size"
)
WriteRequest.__doc__ = """Modbus Write Request Protocol Data Unit (PDU)

Attrs:
    start (int): Address of (first) register to write
    count (int): Number fo coils/registers to write
    size (int): Number of payload bytes to write

Note:
    A PDU usually starts with a single byte containing the function code, which
    is part of the :class:`~modbusclient.ApplicationProtocolHeader` in this
    implementation.
"""

SingleWriteRequest = __create_header(
    name="SingleWriteRequest",
    format="H",
    attrs="start"
)
SingleWriteRequest.__doc__ = """Modbus Write Request Protocol Data Unit (PDU) for a single register

Attrs:
    start (int): Address of (first) register to write

Note:
    A PDU usually starts with a single byte containing the function code, which
    is part of the :class:`~modbusclient.ApplicationProtocolHeader` in this
    implementation.
"""

ReadResponse = __create_header(
    name="ReadResponse",
    format="B",
    attrs="size"
)
ReadResponse.__doc__ = """Modbus Response Protocol Data Unit (PDU)

Attrs:
    size (int): Number of payload bytes to follow

Note:
    A PDU usually starts with a single byte containing the function code, which
    is part of the :class:`~modbusclient.ApplicationProtocolHeader` in this
    implementation.
"""

WriteResponse = __create_header(
    name="WriteResponse",
    format="2H",
    attrs="start count"
)
WriteResponse.__doc__ = """Modbus Response Protocol Data Unit (PDU)

Attrs:
    start (int): Address of (first) register written
    count (int): Number of coils/registers written

Note:
    A PDU usually starts with a single byte containing the function code, which
    is part of the :class:`~modbusclient.ApplicationProtocolHeader` in this
    implementation.
"""

SingleWriteResponse = __create_header(
    name="SingleWriteResponse",
    format="H",
    attrs="start"
)
SingleWriteResponse.__doc__ = """Modbus Response Protocol Data Unit (PDU) for a single write

Attrs:
    start (int): Address of (first) register written

Note:
    A PDU usually starts with a single byte containing the function code, which
    is part of the :class:`~modbusclient.ApplicationProtocolHeader` in this
    implementation.
"""

Error = __create_header(
    name="Error",
    format="B",
    attrs="exception_code"
)
Error.__doc__= """Modbus Error Protocol Data Unit (PDU)

PDU sent on errors by the server. 

Attrs:
    exception_code (int): Exception code.

Note:
    A PDU usually starts with a single byte containing the function code, which
    is part of the :class:`~modbusclient.ApplicationProtocolHeader` in this
    implementation.
"""

REQUEST_TYPES = {
    READ_HOLDING_REGISTERS : ReadRequest,
    READ_INPUT_REGISTERS : ReadRequest,
    WRITE_MULTIPLE_REGISTERS : WriteRequest,
    WRITE_SINGLE_REGISTER : SingleWriteRequest
    # TODO ...
}

RESPONSE_TYPES = {
    READ_HOLDING_REGISTERS : ReadResponse,
    READ_INPUT_REGISTERS : ReadResponse,
    WRITE_MULTIPLE_REGISTERS : WriteResponse,
    WRITE_SINGLE_REGISTER : SingleWriteResponse
}


def new_request(
    function: int,
    payload: bytes = b"",
    unit: int = NO_UNIT,
    transaction: int = 0,
    **kwargs) -> tuple[ApplicationProtocolHeader, bytes]:
    """Create request message

    Args:
        function: Function code
        payload: Data sent along with the request. Used only for writing
            functions. Empty by default.
        unit: Unit ID of the device. Defaults to NO_UNIT
        transaction: Transaction ID. Defaults to 0.
        kwargs: Keyword arguments passed verbatim to the request of
          the function

    Return:
        tuple(~modbusclient.ApplicationProtocolHeader, bytes): Header of the
        request and the request itself in binary form.
    """
    try:
        RequestType = REQUEST_TYPES[function]
    except KeyError:
        raise RuntimeError("Unsupported Function ID", function)
    logger.debug("Creating %s request", str(RequestType))
    if payload:
        kwargs['size'] = len(payload)

    # Ignore arguments not recognized by RequestType
    known_args = {k: kwargs[k] for k in kwargs.keys() & RequestType._fields}
    request = RequestType(**known_args)
    nbytes = 2 + len(request) + kwargs.get('size', 0)
    header = ApplicationProtocolHeader(
        transaction=transaction,
        protocol=MODBUS_PROTOCOL_ID,
        length=nbytes,
        unit=unit,
        function=function
    )
    buffer = b"".join([header.to_buffer(), request.to_buffer(), payload])
    return header, buffer


def parse_response_header(buffer: bytes) -> ApplicationProtocolHeader:  # pyright: ignore[reportInvalidTypeForm]
    """Parse response header

    Args:
        buffer: Buffer containing the Application protocol header

    Return:
        Application protocol header

    Raise:
        RuntimeError: if header.protocol does not match MODBUS_PROTOCOL_ID
    """
    logger.debug("Parsing Application Protocol header ...")
    header = ApplicationProtocolHeader.from_buffer(buffer)

    if header.protocol != MODBUS_PROTOCOL_ID:
        raise RuntimeError("Invalid protocol ID", header.protocol)

    return header


def parse_response_body(
    header: ApplicationProtocolHeader,
    buffer: bytes
) -> tuple[bytes, int]:
    """Parse response body

    Args:
        header: The header. Ref. :func:`parse_response_header`
        buffer: Buffer containing the response body following the header

    Return:
        Payload and error code
    """
    logger.debug("Parsing response body ...")
    if header.function > ERROR_FLAG:  # second byte = function code
        msg = Error.from_buffer(buffer)
        err_code = msg.exception_code
        payload = b""
    else:
        response_type = RESPONSE_TYPES[header.function]
        msg = response_type.from_buffer(buffer)
        payload = buffer[len(msg):]

        if payload and (len(payload) != getattr(msg, "size", 2)):
            err_code = MESSAGE_SIZE_ERROR
        else:
            err_code = NO_ERROR
    return payload, err_code
