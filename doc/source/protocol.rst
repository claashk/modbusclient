The Modbus Protocol
===================

There are a number of good online resources describing the Modbus protocol. Thus
we only cover the basics here, which are essential to understand this
implementation. The reader is referred to the `Modbus Homepage`_ for detailed
information.

Modbus is a binary protocol, which consists of messages passed between a server
and a client. Several transport protocols are possible, but this implementation
exclusively supports TCP/IP as transport layer. Each Modbus message is composed
of three components:

* A seven byte long Modbus Application Protocol Header (MBAP,
  see :class:`~modbusclient.ApplicationProtocolHeader`), which is actually eight
  bytes long in this implementation.
* A message specific header called Protocol Data Unit (PDU)
* An API specific payload of variable length

Each message sent to the client initiates the invocation of a function on the
server. The result of this function is then returned to the client. The functions
can be used to read or manipulate data on the server. The data is stored in
so-called coils and registers. A coil is the equivalent to a bit, while a
register contains 16-bits of data. The registers are addressed by decimal
numbers. Modbus desriminates between *Input Registers* (read-only) and *Holding
Registers* (read-write).

The organisation of data in registers and coils is API/vendor specific.

.. _Modbus Homepage: http://www.modbus.org
.. _Official Modbus Documentation: http://www.modbus.org/specs.php
.. _Modbus Page at Wikipedia: https://en.wikipedia.org/wiki/Modbus

Links
-----

* `Modbus Homepage`_
* `Official Modbus Documentation`_
* `Modbus Page at Wikipedia`_

Protocol Implementation
=======================

Parser Functions
----------------

The following functions can be used to create requests in binary form and to
parse binary response messages:

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