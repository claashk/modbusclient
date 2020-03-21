API Templates
=============

In order to set you up quickly, there are two API templates, which allow to
create a Modbus client from a simple API definition. The API definition is
assumed to be provided in terms of a dictionary, which contains a meaningful
key (such as the numeric message ID or a string) as key and a
:class:`~modbusclient.Payload` object as value.

Default API Template
====================

.. autoclass:: modbusclient.api.DefaultApi
   :members:
   :special-members: __enter__, __exit__
   :no-undoc-members:

Asynchronous API Template
=========================

.. autoclass:: modbusclient.asyncio.api.DefaultApi
   :members:
   :special-members: __aenter__, __aexit__
   :no-undoc-members:
