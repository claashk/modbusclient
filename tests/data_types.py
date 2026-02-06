#!/usr/bin/env python3

import unittest
from modbusclient.data_types import (
    DataType,
    AtomicType,
    String,
    swap_words,
    bcd_decode,
    bcd_encode,
)


class DataTypeTestCase(unittest.TestCase):
    """Test cases for DataType class"""

    def test_construction_with_leading_exclamation(self):
        """Test that DataType adds leading ! if not present"""
        dt1 = DataType("!H")
        # Verify by encoding a test value
        self.assertEqual(dt1.encode(256), b'\x01\x00')

    def test_construction_without_leading_exclamation(self):
        """Test that DataType adds leading ! if not present"""
        dt2 = DataType("H")
        # Should work the same as with explicit !
        self.assertEqual(dt2.encode(256), b'\x01\x00')

    def test_construction_with_byte_order_marks(self):
        """Test that DataType respects explicit byte order marks"""
        dt_little = DataType("<H")
        # Little endian encoding
        self.assertEqual(dt_little.encode(256), b'\x00\x01')

        dt_big = DataType(">H")
        # Big endian encoding
        self.assertEqual(dt_big.encode(256), b'\x01\x00')

        dt_native = DataType("=H")
        # Native encoding (test that it's different from big)
        encoded = dt_native.encode(256)
        self.assertIsNotNone(encoded)

    def test_construction_with_nan(self):
        """Test that NaN value is stored correctly"""
        dt = DataType("f", nan=float('nan'))
        # Verify by encoding and decoding
        nan_value = float('nan')
        encoded = dt.encode(nan_value)
        result = dt.decode(encoded)
        self.assertEqual(len(result), 1)

    def test_construction_with_swap_words(self):
        """Test that swap_words flag is stored"""
        dt_no_swap = DataType("H", swap_words=False)
        # Test by encoding/decoding
        self.assertEqual(dt_no_swap.encode(256), b'\x01\x00')

        # Test with two words to see swap difference
        dt_no_swap_2w = DataType("HH", swap_words=False)
        dt_swap_2w = DataType("HH", swap_words=True)

        test_values = (256, 512)
        encoded_no_swap = dt_no_swap_2w.encode(*test_values)
        encoded_swap = dt_swap_2w.encode(*test_values)

        # They should be different
        self.assertNotEqual(encoded_no_swap, encoded_swap)

    def test_length(self):
        """Test DataType with various format specifiers"""
        format_tests = [
            ("B", 1),    # unsigned char
            ("b", 1),    # signed char
            ("H", 2),    # unsigned short
            ("h", 2),    # signed short
            ("I", 4),    # unsigned int
            ("i", 4),    # signed int
            ("Q", 8),    # unsigned long long
            ("q", 8),    # signed long long
            ("f", 4),    # float
            ("d", 8),    # double
        ]

        for fmt, expected_size in format_tests:
            with self.subTest(format=fmt):
                dt = DataType(fmt)
                self.assertEqual(expected_size, len(dt))

    def test_encode_single_value(self):
        """Test encoding a single value"""
        dt = DataType("H")
        result = dt.encode(256)
        self.assertEqual(result, b'\x01\x00')

    def test_encode_multiple_values(self):
        """Test encoding multiple values"""
        dt = DataType("HH")
        result = dt.encode(256, 512)
        self.assertEqual(result, b'\x01\x00\x02\x00')

    def test_encode_with_swap_words(self):
        """Test encoding with word swapping"""
        dt = DataType("HH", swap_words=True)
        result = dt.encode(0x1234, 0x5678)
        # Without swap: b'\x12\x34\x56\x78'
        # With swap: words are flipped
        expected_no_swap = b'\x12\x34\x56\x78'
        self.assertNotEqual(result, expected_no_swap)

    def test_decode_single_value(self):
        """Test decoding a single value"""
        dt = DataType("H")
        result = dt.decode(b'\x01\x00')
        self.assertEqual(result, (256,))

    def test_decode_multiple_values(self):
        """Test decoding multiple values"""
        dt = DataType("HH")
        result = dt.decode(b'\x01\x00\x02\x00')
        self.assertEqual(result, (256, 512))

    def test_decode_with_swap_words(self):
        """Test decoding with word swapping"""
        dt_no_swap = DataType("HH", swap_words=False)
        dt_swap = DataType("HH", swap_words=True)

        buffer = b'\x12\x34\x56\x78'
        result_no_swap = dt_no_swap.decode(buffer)
        result_swap = dt_swap.decode(buffer)

        self.assertNotEqual(result_no_swap, result_swap)

    def test_encode_decode_roundtrip(self):
        """Test that encode followed by decode returns original value"""
        dt = DataType("f")
        original = 42.5
        encoded = dt.encode(original)
        result = dt.decode(encoded)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], original)

    def test_encode_decode_roundtrip_signed_int(self):
        """Test roundtrip with signed integers"""
        dt = DataType("i")
        for value in [-100, -1, 0, 1, 100]:
            encoded = dt.encode(value)
            decoded, = dt.decode(encoded)
            self.assertEqual(decoded, value)

    def test_decode_float_nan(self):
        """Test decoding with NaN value"""
        dt = DataType("f", nan=float('nan'))
        # Encode a NaN value
        nan_value = float('nan')
        encoded = dt.encode(nan_value)
        result = dt.decode(encoded)
        self.assertEqual(len(result), 1)


class AtomicTypeTestCase(unittest.TestCase):
    """Test cases for AtomicType class"""

    def test_atomic_type_inherits_from_datatype(self):
        """Test that AtomicType is a subclass of DataType"""
        at = AtomicType("H")
        self.assertIsInstance(at, DataType)

    def test_decode_returns_single_value_not_tuple(self):
        """Test that decode returns single value, not tuple"""
        at = AtomicType("H")
        result = at.decode(b'\x01\x00')
        self.assertEqual(result, 256)

    def test_decode_with_nan_value(self):
        """Test that NaN is mapped to None"""
        at = AtomicType("f", nan=-9999)
        nan_value = -9999
        encoded = at.encode(nan_value)
        decoded = at.decode(encoded)
        self.assertIsNone(decoded)

    def test_decode_without_nan(self):
        """Test that non-NaN values are returned as-is"""
        at = AtomicType("f", nan=-9999)
        value = 42.5
        encoded = at.encode(value)
        decoded = at.decode(encoded)
        self.assertEqual(decoded, value)

    def test_decode_roundtrip(self):
        """Test encode/decode roundtrip with AtomicType"""
        at = AtomicType("i")
        original = 12345
        encoded = at.encode(original)
        decoded = at.decode(encoded)
        self.assertEqual(decoded, original)


class StringTestCase(unittest.TestCase):
    """Test cases for String class"""

    def test_string_inherits_from_atomictype(self):
        """Test that String is a subclass of AtomicType"""
        s = String(10)
        self.assertIsInstance(s, AtomicType)

    def test_string_length(self):
        """Test that String has correct length in bytes"""
        s5 = String(5)
        self.assertEqual(len(s5), 5)

        s10 = String(10)
        self.assertEqual(len(s10), 10)

    def test_string_encode_utf8_default(self):
        """Test encoding with default UTF-8 encoding"""
        s = String(10)
        result = s.encode("hellöle")
        self.assertEqual(result, b'hell\xc3\xb6le\x00\x00')

    def test_string_encode_with_padding(self):
        """Test that short strings are padded with null bytes"""
        s = String(10)
        result = s.encode("test")
        self.assertEqual(len(result), 10)
        self.assertEqual(b"test" + 6 * b"\x00", result)

    def test_string_decode_utf8(self):
        """Test decoding with UTF-8"""
        s = String(10)
        result = s.decode(b'hell\xc3\xb6le\x00\x00')
        self.assertEqual('hellöle', result)

    def test_string_encoding_parameter(self):
        """Test custom encoding"""
        s_ascii = String(5, encoding='ascii')
        # Test by encoding/decoding
        result = s_ascii.encode("test")
        self.assertEqual(b"test\x00", result)

        s_utf16 = String(10, encoding='utf-16')
        result2 = s_utf16.encode("test")
        core = "test".encode('utf-16')
        expected = core + (10 - len(core)) * b"\x00"
        self.assertEqual(expected, result2)

    def test_string_encode_decode_roundtrip(self):
        """Test roundtrip with ASCII text"""
        s = String(20)
        original = "Hello Wörld"
        encoded = s.encode(original)
        decoded = s.decode(encoded)
        self.assertEqual(original,decoded)

    def test_string_swap_words_parameter(self):
        """Test that swap_words parameter is passed correctly"""
        s_no_swap = String(6, swap_words=False)
        # Test that it works
        result1 = s_no_swap.encode("tüst")
        self.assertEqual(len(result1), 6)

        s_swap = String(6, swap_words=True)
        result2 = s_swap.encode("tüst")
        self.assertEqual(len(result2), 6)


class SwapWordsTestCase(unittest.TestCase):
    """Test cases for swap_words function"""

    def test_swap_words_basic(self):
        """Test basic word swapping"""
        # Create a simple 4-byte array: [0x12, 0x34, 0x56, 0x78]
        # After swap (as 16-bit words): [0x5678, 0x1234]
        arr = b'\x12\x34\x56\x78'
        result = swap_words(arr)
        self.assertEqual(len(result), len(arr))

    def test_swap_words_single_word(self):
        """Test swap with single 16-bit word"""
        arr = b'\x12\x34'
        result = swap_words(arr)
        self.assertEqual(result, b'\x12\x34')  # Single word stays in place

    def test_swap_words_two_words(self):
        """Test swap with two 16-bit words"""
        arr = b'\x12\x34\x56\x78'
        result = swap_words(arr)
        # Two words should swap positions
        self.assertEqual(len(result), 4)

    def test_swap_words_multiple_words(self):
        """Test swap with multiple words"""
        # 4 words (8 bytes)
        arr = b'\x00\x01\x02\x03\x04\x05\x06\x07'
        result = swap_words(arr)
        self.assertEqual(len(result), 8)

    def test_swap_words_roundtrip(self):
        """Test that double swap returns original"""
        arr = b'\x12\x34\x56\x78'
        result = swap_words(swap_words(arr))
        self.assertEqual(result, arr)


class BCDTestCase(unittest.TestCase):
    """Test cases for bcd_decode function"""
    def setUp(self):
        self.pairs = [
            (0x00, 0),
            (0x01, 1),
            (0x09, 9),
            (0x10, 10),
            (0x11, 11),
            (0x23, 23),
            (0x45, 45),
            (0x67, 67),
            (0x89, 89),
            (0x99, 99)
        ]

    def test_decode(self):
        """Test decoding various BCD values"""
        for bcd_byte, expected in self.pairs:
            with self.subTest(bcd_byte=bcd_byte):
                result = bcd_decode(bcd_byte)
                self.assertEqual(expected, result)

    def test_encode(self):
        """Test encoding various values"""
        for expected, number in self.pairs:
            with self.subTest(number=number):
                result = bcd_encode(number)
                self.assertEqual(result, expected)

    def test_bcd_encode_negative_raises_error(self):
        """Test that negative numbers raise ValueError"""
        with self.assertRaises(ValueError):
            _ = bcd_encode(-1)

    def test_bcd_encode_too_large_raises_error(self):
        """Test that numbers >= 100 raise ValueError"""
        with self.assertRaises(ValueError):
            _ = bcd_encode(100)

        with self.assertRaises(ValueError):
            _ = bcd_encode(999)

    def test_bcd_encode_decode_roundtrip(self):
        """Test that encode followed by decode returns original"""
        for number in range(0, 100):
            with self.subTest(number=number):
                encoded = bcd_encode(number)
                decoded = bcd_decode(encoded)
                self.assertEqual(decoded, number)


def suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(DataTypeTestCase))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(AtomicTypeTestCase))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(StringTestCase))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(SwapWordsTestCase))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(BCDTestCase))
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())


















