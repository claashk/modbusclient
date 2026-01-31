User Data
=========

The handling of user data is not specified by the Modbus protocol. In principle,
any sequence of bytes can be sent as payload. In order to support a variety of
use cases, there exist two building blocks for user data:

* Class (:class:`~modbusclient.data_type.DataType`) and derived classes implement
  the actual storage layout of the payload, including the translation from and
  to byte sequences.
* Class :class:`~modbusclient.payload.Payload` and classes derived from it wrap a
  :class:`~modbusclient.data_type.DataType` to provide a generic interface to
  store metadata and to perform scaling.

The various payload types are described in chapter `Payload Types`_. For more
information on data types, refer to chapter `Data Types`_.

Payload Types
=============

Payload Base
------------

.. autoclass:: modbusclient.payload.Payload
   :members:
   :special-members: __len__, __str__, __hash__, __ne__, __eq__
   :no-undoc-members:


Fixpoint Floating Point
-----------------------

.. autoclass:: modbusclient.Fixpoint
   :members:
   :special-members: __len__, __str__, __hash__, __ne__, __eq__
   :show-inheritance:
   :inherited-members:
   :no-undoc-members:

Enumeration Type
----------------

.. autoclass:: modbusclient.Enum
   :members:
   :special-members: __len__, __str__, __hash__, __ne__, __eq__
   :show-inheritance:
   :inherited-members:
   :no-undoc-members:


Data Types
==========

This implementation provides several basic datatypes, which can be wrapped in a
:class:`~modbusclient.payload.Payload` object.

Base Class for Data Types
-------------------------

The data type class is a base class for datatypes, which provides an interface
compatible with ``

.. autoclass:: modbusclient.data_types.DataType
   :members:
   :special-members:
   :show-inheritance:
   :inherited-members:
   :no-undoc-members:

Numeric Types
-------------

An data type intended for atomic numeric types such as integers or floats of
varying precision.

.. autoclass:: modbusclient.data_types.AtomicType

String Types
------------

.. autoclass:: modbusclient.data_types.String

Helper Functions
----------------

The following two functions may come in handy, when you have to create your own
data type for Binary Coded Decimal types.

.. autofunction:: modbusclient.data_types.bcd_decode

.. autofunction:: modbusclient.data_types.bcd_decode

.. autofunction:: modbusclient.data_types.swap_words



