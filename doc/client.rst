Clients
=======

The TCP connection to the server can be established by a synchronous or
asynchronous client.

Default Client
==============

.. autoclass:: modbusclient.client.Client
   :members:
   :special-members: __enter__, __exit__
   :no-undoc-members:

Asynchronous Client
===================

.. autoclass:: modbusclient.asyncio.Client
   :members:
   :special-members: __aenter__, __aexit__
   :no-undoc-members:
