from typing import ClassVar
try:
    from collections.abc import Buffer
except ImportError:
    from collections.abc import ByteString as Buffer

import dataclasses
import logging
from dataclasses import dataclass
from struct import Struct

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


class HeaderMixin:
    """Mixing for the different header types

    Adds methods to parse and serialize the header in binary form and to get the
    length of the header in bytes.
    """
    format: ClassVar[str]
    parser: ClassVar[Struct | None] = None

    def __len__(self) -> int:
        """Get length of current message in bytes

        Return:
            int: Length of current message in packed binary form
        """
        return self.get_parser().size

    def to_buffer(self) -> bytes:
        """Write current message to buffer in packed binary form

        Invokes the internal parser to create a bytes object representing the
        current instance in packed binary form

        Return:
            bytes: String containing current instance in packed binary form
        """
        return self.get_parser().pack(*dataclasses.astuple(self))

    @classmethod
    def get_parser(cls) -> Struct:
        if cls.parser is None:
            cls.parser = Struct("!" + cls.format)
        return cls.parser

    @classmethod
    def from_buffer(cls, buffer: Buffer, offset: int=0) -> object:
        """Create message from buffer

        Invokes the parser on a buffer an returns the class created from the
        data extracted from the buffer

        Args:
            buffer: Buffer containing packed binary data
            offset: Number of bytes to skip at front of buffer. Defaults
                to zero.

        Return:
            Instance of derived class created from binary data
        """
        return cls(*cls.get_parser().unpack_from(buffer, offset))

    @classmethod
    def get_fields(cls) -> list[str]:
        """Get names of accepted arguments / fields
        """
        return [f.name for f in dataclasses.fields(cls)]


@dataclass
class ApplicationProtocolHeader(HeaderMixin):
    """Modbus Application Protocol Header (MBAP)

    The application header in this implementation has a size of eight bytes. It is
    added to every request sent by a client. The server copies the MBAP into its
    response with a modified length field.

    Attrs:
        transaction: Transaction ID to uniquely identify the transaction if
            several requests are sent in parallel
        protocol: MODBUS protocol id (always 0)
        msglen: Number of bytes including the unit identifier byte and all
           following data bytes. For a request, this has to be set by the client,
           while the response length is set by the server
        unit: Unit ID of the server. Defaults to NO_UNIT
        function: Function code. Assumes the error function code (0x80) if an
            error is encountered. In the MODBUS specification this is part of the
            PDU, but in order to simplify the communication, we include it into the
            MBAP here.
    """
    format: ClassVar[str] = "3H2B"
    transaction: int = 1
    protocol: int = 0
    msglen: int = 0
    unit: int = 3
    function: int = 0x80


@dataclass
class ReadRequest(HeaderMixin):
    """Modbus Read Request Protocol Data Unit (PDU)

    Attrs:
        start: Address of (first) register to read
        count: Number of coils/registers to read

    Note:
        A PDU usually starts with a single byte containing the function code, which
        is part of the :class:`~modbusclient.ApplicationProtocolHeader` in this
        implementation.
    """
    format: ClassVar[str] = "2H"
    start: int = 0
    count: int = 0


@dataclass
class WriteRequest(HeaderMixin):
    """Modbus Write Request Protocol Data Unit (PDU)

    Attrs:
        start: Address of (first) register to write
        count: Number fo coils/registers to write
        size: Number of payload bytes to write

    Note:
        A PDU usually starts with a single byte containing the function code, which
        is part of the :class:`~modbusclient.ApplicationProtocolHeader` in this
        implementation.
    """
    format: ClassVar[str] = "2HB"
    start: int = 0
    count: int = 0
    size: int = 0


@dataclass
class SingleWriteRequest(HeaderMixin):
    """Modbus Write Request Protocol Data Unit (PDU) for a single register

    Attrs:
        start: Address of (first) register to write

    Note:
        A PDU usually starts with a single byte containing the function code, which
        is part of the :class:`~modbusclient.ApplicationProtocolHeader` in this
        implementation.
    """
    format: ClassVar[str] = "H"
    start: int = 0


@dataclass
class ReadResponse(HeaderMixin):
    """Modbus Response Protocol Data Unit (PDU)

    Attrs:
        size: Number of payload bytes to follow

    Note:
        A PDU usually starts with a single byte containing the function code, which
        is part of the :class:`~modbusclient.ApplicationProtocolHeader` in this
        implementation.
    """
    format: ClassVar[str] = "B"
    size: int = 0


@dataclass
class WriteResponse(HeaderMixin):
    """Modbus Response Protocol Data Unit (PDU)

    Attrs:
        start: Address of (first) register written
        count: Number of coils/registers written

    Note:
        A PDU usually starts with a single byte containing the function code, which
        is part of the :class:`~modbusclient.ApplicationProtocolHeader` in this
        implementation.
    """
    format: ClassVar[str] = "2H"
    start: int = 0
    count: int = 0


@dataclass
class SingleWriteResponse(HeaderMixin):
    """Modbus Response Protocol Data Unit (PDU) for a single write

    Attrs:
        start: Address of (first) register written

    Note:
        A PDU usually starts with a single byte containing the function code, which
        is part of the :class:`~modbusclient.ApplicationProtocolHeader` in this
        implementation.
    """
    format: ClassVar[str] = "H"
    size: ClassVar[int] = 2  # always 2 bytes, so we use a class variable here
    start: int = 0


@dataclass
class Error(HeaderMixin):
    """Modbus Error Protocol Data Unit (PDU)

    PDU sent on errors by the server.

    Attrs:
        exception_code: Exception code.

    Note:
        A PDU usually starts with a single byte containing the function code, which
        is part of the :class:`~modbusclient.ApplicationProtocolHeader` in this
        implementation.
    """
    format: ClassVar[str] = "B"
    exception_code: int = 0


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
    # TODO ...
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

    Raises:
        TypeError: If any keyword argument is not recognized
    """
    try:
        RequestType = REQUEST_TYPES[function]
    except KeyError:
        raise RuntimeError("Unsupported Function ID", function)
    logger.debug(f"Creating {RequestType} request")
    if payload:
        kwargs['size'] = len(payload)

    # It is considered an error to pass arguments not recognized by request type
    request = RequestType(**kwargs)
    msglen = 2 + len(request) + getattr(request, "size", 0)
    header = ApplicationProtocolHeader(
        transaction=transaction,
        protocol=MODBUS_PROTOCOL_ID,
        msglen=msglen,
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
        header: Header as returned by :func:`parse_response_header`
        buffer: Buffer containing the response body following the header

    Return:
        Payload and error code

    Raises:
        struct.error if buffer is smaller than required for PDU
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

        if len(payload) != getattr(msg, "size", 0):
            err_code = MESSAGE_SIZE_ERROR
        else:
            err_code = NO_ERROR
    return payload, err_code
