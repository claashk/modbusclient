WAMP Client
===========

In order to use an asynchronous Modbus Client as WAMP component, there exists
a thin wrapper around the API baseclass, which turns the API implementation into
a WAMP component. The wrapper uses the Autobahn WAMP framework, which allows to
integrate seamlessly with the crossbar.io router, which supports WAMP and
MQTT environments out of the box.

Base Class for WAMP Components
==============================

.. autoclass:: modbusclient.asyncio.autobahn.ComponentBase
   :members:
   :no-undoc-members:
