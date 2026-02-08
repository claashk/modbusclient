#!/usr/bin/env python3
import unittest
import struct

from modbusclient.protocol import (
    ApplicationProtocolHeader,
    ReadRequest,
    WriteRequest,
    SingleWriteRequest,
    ReadResponse,
    WriteResponse,
    SingleWriteResponse,
    Error,
    new_request,
    parse_response_header,
    parse_response_body,
    REQUEST_TYPES,
    RESPONSE_TYPES,
    MODBUS_PROTOCOL_ID,
    NO_UNIT,
    DEFAULT_PORT
)
from modbusclient.error_codes import ERROR_MESSAGES, NO_ERROR, MESSAGE_SIZE_ERROR
from modbusclient.functions import (
    READ_HOLDING_REGISTERS,
    READ_INPUT_REGISTERS,
    WRITE_MULTIPLE_REGISTERS,
    WRITE_SINGLE_REGISTER,
    ERROR_FLAG
)


class TestApplicationProtocolHeader(unittest.TestCase):
    """Test ApplicationProtocolHeader (MBAP)"""

    def test_default_values(self):
        """Test MBAP default values"""
        header = ApplicationProtocolHeader()
        self.assertEqual(1, header.transaction)
        self.assertEqual(0, header.protocol)
        self.assertEqual(0, header.msglen)
        self.assertEqual(3, header.unit)
        self.assertEqual(0x80, header.function)

    def test_custom_values(self):
        """Test MBAP with custom values"""
        header = ApplicationProtocolHeader(
            transaction=42,
            protocol=0,
            msglen=10,
            unit=1,
            function=3
        )
        self.assertEqual(42, header.transaction)
        self.assertEqual(1, header.unit)
        self.assertEqual(3, header.function)
        self.assertEqual(0, header.protocol)
        self.assertEqual(10, header.msglen)

    def test_header_round_trip(self):
        """Test serialization and deserialization round trip"""
        original = ApplicationProtocolHeader(
            transaction=100,
            protocol=0,
            msglen=20,
            unit=5,
            function=16
        )
        buffer = original.to_buffer()
        restored = ApplicationProtocolHeader.from_buffer(buffer)
        self.assertEqual(original.transaction, restored.transaction)
        self.assertEqual(original.protocol, restored.protocol)
        self.assertEqual(original.msglen, restored.msglen)
        self.assertEqual(original.unit, restored.unit)
        self.assertEqual(original.function, restored.function)


class TestReadRequest(unittest.TestCase):
    """Test ReadRequest PDU"""

    def test_read_request_creation(self):
        """Test creating read request"""
        req = ReadRequest(start=100, count=10)
        self.assertEqual(100, req.start)
        self.assertEqual(10, req.count)

    def test_read_request_round_trip(self):
        """Test serialization and deserialization"""
        original = ReadRequest(start=500, count=25)
        buffer = original.to_buffer()
        restored = ReadRequest.from_buffer(buffer)

        self.assertEqual(len(original), len(buffer))
        self.assertEqual(original.start, restored.start)
        self.assertEqual(original.count, restored.count)


class TestWriteRequest(unittest.TestCase):
    """Test WriteRequest PDU"""

    def test_write_request_creation(self):
        """Test creating write request"""
        req = WriteRequest(start=100, count=2, size=4)
        self.assertEqual(100, req.start)
        self.assertEqual(2, req.count)
        self.assertEqual(4, req.size)

    def test_write_request_round_trip(self):
        """Test serialization and deserialization"""
        original = WriteRequest(start=200, count=5, size=10)
        buffer = original.to_buffer()
        restored = WriteRequest.from_buffer(buffer)

        self.assertEqual(len(original), len(buffer))
        self.assertEqual(original.start, restored.start)
        self.assertEqual(original.count, restored.count)
        self.assertEqual(original.size, restored.size)


class TestSingleWriteRequest(unittest.TestCase):
    """Test SingleWriteRequest PDU"""

    def test_single_write_request_creation(self):
        """Test creating single write request"""
        req = SingleWriteRequest(start=100)
        self.assertEqual(100, req.start)

    def test_single_write_request_round_trip(self):
        """Test serialization and deserialization"""
        original = SingleWriteRequest(start=1000)
        buffer = original.to_buffer()
        restored = SingleWriteRequest.from_buffer(buffer)

        self.assertEqual(len(original), len(buffer))
        self.assertEqual(original.start, restored.start)


class TestReadResponse(unittest.TestCase):
    """Test ReadResponse PDU"""

    def test_read_response_creation(self):
        """Test creating read response"""
        resp = ReadResponse(size=10)
        self.assertEqual(10, resp.size)

    def test_read_response_round_trip(self):
        """Test serialization and deserialization"""
        original = ReadResponse(size=50)
        buffer = original.to_buffer()
        restored = ReadResponse.from_buffer(buffer)

        self.assertEqual(len(original), len(buffer))
        self.assertEqual(original.size, restored.size)


class TestWriteResponse(unittest.TestCase):
    """Test WriteResponse PDU"""

    def test_write_response_creation(self):
        """Test creating write response"""
        resp = WriteResponse(start=100, count=2)
        self.assertEqual(100, resp.start)
        self.assertEqual(2, resp.count)

    def test_write_response_round_trip(self):
        """Test serialization and deserialization"""
        original = WriteResponse(start=500, count=100)
        buffer = original.to_buffer()
        restored = WriteResponse.from_buffer(buffer)

        self.assertEqual(len(original), len(buffer))
        self.assertEqual(original.start, restored.start)
        self.assertEqual(original.count, restored.count)


class TestSingleWriteResponse(unittest.TestCase):
    """Test SingleWriteResponse PDU"""

    def test_single_write_response_creation(self):
        """Test creating single write response"""
        resp = SingleWriteResponse(start=100)
        self.assertEqual(100, resp.start)
        self.assertEqual(2, resp.size)
        self.assertNotIn("size", resp.get_fields())


class TestError(unittest.TestCase):
    """Test Error PDU"""

    def test_error_creation(self) -> None:
        """Test creating error message"""
        err = Error(exception_code=2)
        self.assertEqual(2, err.exception_code)

    def test_error_all_exception_codes(self) -> None:
        """Test various exception codes"""
        for code in [1, 2, 3, 4, 5, 6, 8, 10, 11]:
            err = Error(exception_code=code)
            buffer = err.to_buffer()
            restored = Error.from_buffer(buffer)
            self.assertEqual(code, restored.exception_code)


class TestRequestTypes(unittest.TestCase):
    """Test REQUEST_TYPES dictionary"""

    def test_request_types_correct_classes(self):
        """Test that REQUEST_TYPES maps to correct PDU classes"""
        self.assertEqual(ReadRequest, REQUEST_TYPES[READ_HOLDING_REGISTERS])
        self.assertEqual(ReadRequest, REQUEST_TYPES[READ_INPUT_REGISTERS])
        self.assertEqual(WriteRequest, REQUEST_TYPES[WRITE_MULTIPLE_REGISTERS])
        self.assertEqual(SingleWriteRequest, REQUEST_TYPES[WRITE_SINGLE_REGISTER])


class TestResponseTypes(unittest.TestCase):
    """Test RESPONSE_TYPES dictionary"""

    def test_response_types_correct_classes(self):
        """Test that RESPONSE_TYPES maps to correct PDU classes"""
        self.assertEqual(ReadResponse, RESPONSE_TYPES[READ_HOLDING_REGISTERS])
        self.assertEqual(ReadResponse, RESPONSE_TYPES[READ_INPUT_REGISTERS])
        self.assertEqual(WriteResponse, RESPONSE_TYPES[WRITE_MULTIPLE_REGISTERS])
        self.assertEqual(SingleWriteResponse, RESPONSE_TYPES[WRITE_SINGLE_REGISTER])


class TestNewRequest(unittest.TestCase):
    """Test new_request function"""

    def test_valid_requests(self):
        """Test creating read holding registers request"""

        payload = bytes(range(20))
        all_args = dict(start=10, count=5, payload=payload)

        for func, reqtype in REQUEST_TYPES.items():
            _fields = [
                "payload" if s == "size" else s for s in reqtype.get_fields()
            ]
            kwargs = {k : all_args[k] for k in _fields}
            header, buffer = new_request(function=func, transaction=3, **kwargs)

            hdr = parse_response_header(buffer)
            n = len(payload) if "payload" in _fields else 0
            self.assertEqual(len(buffer), len(hdr) - 2 + header.msglen)
            self.assertEqual(len(buffer), len(hdr) + reqtype.parser.size + n)
            self.assertIsInstance(header, ApplicationProtocolHeader)
            self.assertEqual(func, header.function)
            self.assertEqual(MODBUS_PROTOCOL_ID, header.protocol)
            self.assertEqual(header.function, hdr.function)
            self.assertEqual(header.protocol, hdr.protocol)
            self.assertEqual(len(hdr), len(header))
            self.assertEqual(header.msglen, hdr.msglen)

    def test_new_request_unsupported_function(self):
        """Test that unsupported function raises RuntimeError"""
        with self.assertRaises(RuntimeError):
            new_request(function=999)

    def test_new_request_raises_on_unknown_args(self):
        """Test that unknown kwargs are ignored"""
        with self.assertRaises(TypeError) as ctx:
            header, buffer = new_request(
                function=READ_HOLDING_REGISTERS,
                start=0,
                count=1,
                unknown_param=999
            )
        self.assertIn("'unknown_param'", str(ctx.exception))


class TestParseResponse(unittest.TestCase):
    """Test parse_response_header function"""
    def test_valid_responses(self):
        """Test parsing valid response header"""
        payload = bytes(range(20))
        all_args = dict(start=10, count=5, size=len(payload))

        for func, _type in RESPONSE_TYPES.items():
            kwargs = {k : all_args[k] for k in _type.get_fields()}
            req = _type(**kwargs)
            _size = getattr(req, "size", 0)
            header = ApplicationProtocolHeader(
                function=func,
                unit=2,
                msglen=2 + len(req) + _size
            )
            buffer = b"".join([
                header.to_buffer(),
                req.to_buffer(),
                payload[:_size]  # _size != len(payload) if defined as class var
            ])

            hdr = parse_response_header(buffer)
            _payload, errc = parse_response_body(hdr, buffer[len(hdr):])

            self.assertEqual(header.transaction, hdr.transaction)
            self.assertEqual(header.protocol, hdr.protocol)
            self.assertEqual(header.msglen, hdr.msglen)
            self.assertEqual(2, hdr.unit)
            self.assertEqual(func, hdr.function)
            self.assertEqual(NO_ERROR, errc)
            self.assertEqual(payload[:_size], _payload)

    def test_invalid_protocol(self):
        """Test that invalid protocol ID raises RuntimeError"""
        header = ApplicationProtocolHeader(
            protocol=5,
            function=1,
            unit=2,
            msglen=20
        )

        with self.assertRaises(RuntimeError) as ctx:
            hdr = parse_response_header(header.to_buffer())
        self.assertIn("Invalid protocol ID", str(ctx.exception))

    def test_error_codes(self):
        """Test parsing headers with different transaction IDs"""
        hdr = ApplicationProtocolHeader(function=ERROR_FLAG + 1, msglen=6)

        for ec in ERROR_MESSAGES.keys():
            if ec < 0:
                continue  # library internal error codes cannot be represented
            msg = Error(exception_code=ec)
            payload, errc = parse_response_body(hdr, msg.to_buffer())
            self.assertEqual(b"", payload)
            self.assertEqual(ec, errc)

    def test_message_size_error(self):
        """Test parsing header with error function code"""
        payload = bytes(range(20))
        all_args = dict(start=10, count=5, size=len(payload))

        for func, reqtype in RESPONSE_TYPES.items():
            kwargs = {k : all_args[k] for k in reqtype.get_fields()}
            req = reqtype(**kwargs)
            _size = getattr(req, "size", 0)
            header = ApplicationProtocolHeader(
                function=func,
                unit=2,
                msglen=2 + len(req) + _size
            )
            buffer = b"".join([req.to_buffer(), payload if _size else b""])

            _bufs = [buffer[:-1], buffer[:-_size], buffer + bytes([1])]

            for buf in _bufs:
                if len(buf) < len(req):
                    with self.assertRaises(struct.error):
                        _pl, ec = parse_response_body(header, buf)
                else:
                    _pl, ec = parse_response_body(header, buf)
                    self.assertEqual(ec, MESSAGE_SIZE_ERROR)


class TestConstants(unittest.TestCase):
    """Test module constants"""

    def test_modbus_protocol_id(self):
        """Test MODBUS_PROTOCOL_ID value"""
        self.assertEqual(0, MODBUS_PROTOCOL_ID)

    def test_no_unit(self):
        """Test NO_UNIT value"""
        self.assertEqual(0xFF, NO_UNIT)

    def test_default_port(self):
        """Test DEFAULT_PORT value"""
        self.assertEqual(502, DEFAULT_PORT)


if __name__ == '__main__':
    unittest.main()
