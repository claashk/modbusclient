UNIT_MISMATCH = -3
INVALID_TRANSACTION_ID = -2
MESSAGE_SIZE_ERROR = -1
NO_ERROR = 0
ILLEGAL_FUNCTION_ERROR = 1
ILLEGAL_DATA_ADDRESS = 2
ILLEGAL_DATA_VALUE = 3
SERVER_DEVICE_FAILURE = 4
ACKNOWLEDGE = 5
SERVER_DEVICE_BUSY = 6
MEMORY_PARITY_ERROR = 8
GATEWAY_PATH_UNAVAILABLE = 0xA
GATEWAY_TARGET_FAILED_TO_RESPOND = 0xB

ERROR_MESSAGES = {
    UNIT_MISMATCH: "unit mismatch",
    INVALID_TRANSACTION_ID: "invalid transaction ID",
    MESSAGE_SIZE_ERROR: "message size error",
    ILLEGAL_FUNCTION_ERROR: "illegal function",
    ILLEGAL_DATA_ADDRESS: "illegal data address",
    ILLEGAL_DATA_VALUE: "illegal data value",
    SERVER_DEVICE_FAILURE: "server device failure",
    SERVER_DEVICE_BUSY: "server device busy",
    MEMORY_PARITY_ERROR: "memory parity error",
    GATEWAY_PATH_UNAVAILABLE: "gateway path unavailable",
    GATEWAY_TARGET_FAILED_TO_RESPOND: "gateway target failed to respond"
}

class ModbusError(RuntimeError):
    def __init__(self, err_code, *args):
        super().__init__(err_code, ERROR_MESSAGES[err_code], *args)