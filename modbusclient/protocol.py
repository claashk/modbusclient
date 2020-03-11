
from collections import namedtuple
from struct import Struct
import logging

from .error_codes import MESSAGE_SIZE_ERROR, NO_ERROR
from .functions import *

logger = logging.getLogger('modbusclient')

def message(name, format, attrs, defaults=None):
    """Create a new message class

    Creates a message class based on namedtuple. The class contains additional
    methods to read and write its content to a binary buffer:

    * from_buffer
    * to_buffer

    Arguments:
        name (str): Name of class to create
        format (str): Format string. Refer to Struct documentation for format
            specification
        attrs (str): Attributes to add. Format as expected by namedtuple
        defaults (tuple): Default value for each attribute in attrs

    Return:
        class: Class object
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


ApplicationProtocolHeader = message("ApplicationProtocolHeader",
                                    "3H2B",
                                    "transaction protocol length unit function",
                                    (1, 0, 0, 3, 0x80))
ApplicationProtocolHeader.__doc__ = """Modbus Application Protocol Header (MBAP)

The application header in this implementation has a size of eight bytes and
contains:
* a transaction ID to uniquely identify the transaction in case several requests
  are sent in parallel
* protocol id: 0 for MODBUS
* length: The number of following bytes including the unit identifier byte (and
  all following data bytes). For a request, this has to be set by the client,
  while the response length is set by the server
* Unit ID of the server.
* function code. In the MODBUS specification this is actually part of the PDU,
  but the communication is simplyfied by including it in the MBAP instead. In
  case of errors, this variable assumes the error function code (0x80).

The MBAP is added to every request sent by a client. The server copies the MBAP
into its response. Only the length field will be adapted.
"""

ReadRequest = message("ReadRequest", "2H", "start count")
ReadRequest.__doc__ = """Modbus Read Request Protocol Data Unit (PDU)

The request PDU usually starts with a single byte containing the function code,
which has been moved into the MBAP in this implementation. Requests thus contain
a starting address and the number of registers/coils to read.
"""

WriteRequest = message("WriteRequest", "2HB", "start count size")
WriteRequest.__doc__ = """Modbus Write Request Protocol Data Unit (PDU)

The request PDU usually starts with a single byte containing the function code,
which has been moved into the MBAP in this implementation. Write requests for
multiple coils/registers thus contain a starting address, the number of
registers/coils to read and the size of the data buffer containing the bytes to
write.
"""

ReadResponse = message("ReadResponse", "B", "size")
ReadResponse.__doc__ = """Modbus Response Protocol Data Unit (PDU)

The response PDU usually starts with a single byte containing the function code,
which has been moved into the MBAP in this implementation. Responses thus contain
just the size of the response buffer.

"""

WriteResponse = message("WriteResponse", "2H", "start count")
WriteResponse.__doc__ = """Modbus Response Protocol Data Unit (PDU)

The response PDU usually starts with a single byte containing the function code,
which has been moved into the MBAP in this implementation. Responses to write
opterations of multiple registers thus contain a starting address and the number
of registers, which have been written.
"""

Error = message("Error", "B", "exception_code")
Error.__doc__= """Modbus Error Protocol Data Unit (PDU)

Implementation of the error PDU. It usually starts with a single byte containing
the error function code (0x80), which has been moved into the MBAP in this
implementation. Thus the error PDU contains a single byte containing the
exception code
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

MODBUS_PROTOCOL_ID = 0
NO_UNIT = 0xFF


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
