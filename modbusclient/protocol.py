
from collections import namedtuple
from struct import Struct
import logging

from .error_codes import *
from .functions import *

logger = logging.getLogger('modbusclient')


MODBUS_PROTOCOL_ID = 0
NO_UNIT = 0xFF


def create_header(name, format, attrs, defaults=None):
    """Create a new header

    Creates a header class based on namedtuple. The namedtuple components provide
    a convenient access to the data stored in the header. Additionally classes
    created by this function contain two methods to read from and write to a
    binary buffer:

    * static method from_buffer creates an object from a binary buffer
    * to_buffer: writes content of the header to a binary buffer
    * __len__ : Provides the length of the header (excluding payload) in bytes

    Arguments:
        name (str): Name of class to create
        format (str): Format string. Refer to Struct documentation for format
            specification
        attrs (str): Attributes to add. Format as expected by namedtuple
        defaults (tuple): Default value for each attribute in attrs

    Return:
        class: Class object capable of storing the header content with additional
        methods to parse and serialize the stored data in binary form.
    """
    Base = namedtuple("Base", attrs)

    def new(cls, *args, **kwargs):
        """Create a new class object

        Arguments:
            cls (class): Passed verbatim to Base.__new__
            *args (*args): Positional arguments passed verbatim to Base
            **kwargs (dict): Keyword arguments passed verbatim to Base.__new__
        """
        return Base.__new__(cls, *args, **kwargs)

    @classmethod
    def from_buffer(cls, buffer, offset=0):
        """Create message from buffer

        Invokes the parser on a buffer an returns the class created from the
        data extracted from the buffer

        Arguments:
            cls (class): Class to create
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

    msg_type = type(name, (Base, ), {"format": format,
                                     "parser": Struct("!" + format),
                                     "from_buffer" : from_buffer,
                                     "to_buffer": to_buffer,
                                     "__new__": new,
                                     "__len__": __len__})
    if defaults:
        msg_type.__new__.__defaults__ = tuple(defaults)
    return msg_type


ApplicationProtocolHeader = create_header("ApplicationProtocolHeader",
                                "3H2B",
                                "transaction protocol length unit function",
                                (1, 0, 0, 3, 0x80))
ApplicationProtocolHeader.__doc__ = """Modbus Application Protocol Header (MBAP)

The application header in this implementation has a size of eight bytes. It is
added to every request sent by a client. The server copies the MBAP into its
response with a modified length field.

Attributes:
    transaction (int): Transaction ID to uniquely identify the transaction in
        if several requests are sent in parallel
    protocol (int): MODBUS protocol id (always 0)
    length (int) Number of bytes including the unit identifier byte and all
       following data bytes. For a request, this has to be set by the client,
       while the response length is set by the server
    unit (int): Unit ID of the server. Defaults to NO_UNIT
    function (int): Function code. In the MODBUS specification this is actually
        part of the PDU. Since the communication is simplified by including it in
        the MBAP instead. In case of errors, this variable assumes the error
        function code (0x80).
"""

ReadRequest = create_header("ReadRequest", "2H", "start count")
ReadRequest.__doc__ = """Modbus Read Request Protocol Data Unit (PDU)

Attributes:
    start (int): Address of (first) register to read from
    count (int): Number of coils/registers to read from

Note:
    A PDU usually starts with a single byte containing the function code, which
    is part of the :class:`~modbusclient.ApplicationProtocolHeader` in this
    implementation.
"""

WriteRequest = create_header("WriteRequest", "2HB", "start count size")
WriteRequest.__doc__ = """Modbus Write Request Protocol Data Unit (PDU)

Attributes:
    start (int): Address of (first) register to write to
    count (int): Number fo coils/registers to write to
    size (int): Number of payload bytes to write

Note:
    A PDU usually starts with a single byte containing the function code, which
    is part of the :class:`~modbusclient.ApplicationProtocolHeader` in this
    implementation.
"""

ReadResponse = create_header("ReadResponse", "B", "size")
ReadResponse.__doc__ = """Modbus Response Protocol Data Unit (PDU)

Attributes:
    size (int): Number of payload bytes

Note:
    A PDU usually starts with a single byte containing the function code, which
    is part of the :class:`~modbusclient.ApplicationProtocolHeader` in this
    implementation.
"""

WriteResponse = create_header("WriteResponse", "2H", "start count")
WriteResponse.__doc__ = """Modbus Response Protocol Data Unit (PDU)

Attributes:
    start (int): Address of (first) register to write to
    count (int): Number of coils/registers which have been written

Note:
    A PDU usually starts with a single byte containing the function code, which
    is part of the :class:`~modbusclient.ApplicationProtocolHeader` in this
    implementation.
"""

Error = create_header("Error", "B", "exception_code")
Error.__doc__= """Modbus Error Protocol Data Unit (PDU)

PDU sent on errors by the server. 

Attributes:
    exception_code (int): Exception code.

Note:
    A PDU usually starts with a single byte containing the function code, which
    is part of the :class:`~modbusclient.ApplicationProtocolHeader` in this
    implementation.
"""

REQUEST_TYPES = {
    READ_HOLDING_REGISTER : ReadRequest,
    READ_INPUT_REGISTER : ReadRequest,
    WRITE_MULTIPLE_REGISTERS : WriteRequest
    # TODO ...
}

RESPONSE_TYPES = {
    READ_HOLDING_REGISTER : ReadResponse,
    READ_INPUT_REGISTER : ReadResponse,
    WRITE_MULTIPLE_REGISTERS : WriteResponse
}


def new_request(function, payload=b"", unit=NO_UNIT, transaction=0, **kwargs):
    """Create a request message

    Arguments:
        function (int): Function code
        payload (bytes): Data sent along with the request. Empty by default.
            Used only for writing functions.
        unit (int): Unit ID of device. Defaults to NO_UNIT
        transaction (int): Transaction ID. Defaults to 0.
        kwargs (dict): Keyword arguments passed verbatim to the request of
          the function

    Return:
        tuple(~modbusclient.ApplicationProtocolHeader, bytes): Header of the request
        and the request in binary form.
    """
    try:
        RequestType = REQUEST_TYPES[function]
    except KeyError:
        raise RuntimeError("Unsupported Function ID", function)
    logger.debug("Creating %s request", str(RequestType))
    if payload:
        kwargs['size'] = len(payload)
    request = RequestType(**kwargs)
    nbytes = 2 + len(request) + kwargs.get('size', 0)
    header = ApplicationProtocolHeader(transaction=transaction,
                                       protocol=MODBUS_PROTOCOL_ID,
                                       length=nbytes,
                                       unit=unit,
                                       function=function)
    buffer = b"".join([header.to_buffer(), request.to_buffer(), payload])
    return header, buffer


def parse_response_header(buffer):
    """Parse response header

    Arguments:
        buffer (bytes): Buffer containing the Application protocol header

    Return:
        ~modbusclient.ApplicationProtocolHeader: Application protocol header

    Raise:
        RuntimeError: if header.protocol does not match MODBUS_PROTOCOL_ID
    """
    logger.debug("Parsing Application Protocol header ...")
    header = ApplicationProtocolHeader.from_buffer(buffer)

    if header.protocol != MODBUS_PROTOCOL_ID:
        raise RuntimeError("Invalid protocol ID", header.protocol)

    return header


def parse_response_body(header, buffer):
    """Parse response body

    Arguments:
        header (:class:`~modbusclient.ApplicationProtocolHeader`): The header. See
            e.g. :func:`parse_response_header`
        buffer (bytes): Buffer containing the response body after the header

    Return:
        tuple(object, int): Payload and error code
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

        if payload and (len(payload) != msg.size):
            err_code = MESSAGE_SIZE_ERROR
        else:
            err_code = NO_ERROR
    return payload, err_code
