The Modbus Protocol
===================

There are a number of good documents regarding the Modbus protocol. This
chapter contains a brief summary to present the details necessary to understand
this implementation.

Modbus is a binary protocol, which consists of messages passed between a server
and a client. Each message is composed of three components:

* A seven byte long Modbus Application Protocol Header (MBAP,
  see :class:`~modbusclient.ApplicationProtocolHeader`), which is actuall eight
  bytes long in this implementation.
* A message specific header called Protocol Data Unit (PDU)
* An API specific payload of variable length

Each message sent to the client initiates the invocation of a function on the
server. The result of this function is then returned to the client. The functions
can be used to read or manipulate data on the server. The data is stored in
so-called coils and registers. A coil is the equivalent to a bit, while a
register contains 16-bits of data. The registers are addressed by decimal
numbers.

The organisation of data in registers and coils is API/vendor specific.

Protocol Implementation
=======================

Parser Functions
----------------

The following functions can be used to create requests in binary form and to
parse binary request data

.. autofunction:: modbusclient.new_request

.. autofunction:: modbusclient.parse_response_header

.. autofunction:: modbusclient.parse_response_body

Modbus Application Protocol Header (MBAP)
-----------------------------------------

The application protocol header is the first part of each modbus message.

.. autoclass:: modbusclient.ApplicationProtocolHeader


Read Request PDU
----------------

Protocol Data Unit (PDU) used by the client for read requests.

.. autoclass:: modbusclient.ReadRequest

Read Response PDU
-----------------

Protocol Data Unit (PDU) used by the server to ackknowledge read requests.

.. autoclass:: modbusclient.ReadResponse

Write Request PDU
-----------------

Protocol Data Unit (PDU) used by the client for write requests.

.. autoclass:: modbusclient.WriteRequest

Write Response PDU
------------------

Protocol Data Unit (PDU) used by the server to acknowledge write requests.

.. autoclass:: modbusclient.WriteResponse

Helper Functions
----------------

.. autofunction:: modbusclient.protocol.create_header