API Templates
=============

In order to set you up quickly, there are two API templates, which help to
create a Modbus client from a very simple API definition. The API definition
shall be provided by the user in form a dictionary, which contains the
available sources as :class:`~modbusclient.Payload` as values. The associated
keys for each payload should be specified by the user in terms of suitable
object such as a string or integer containing a unique identifier for the
associated payload.

For more details refer to the class definition of
:class:`modbusclient.api_wrapper.ApiWrapper` (synchronous version) or
:class:`modbusclient.asyncio.api_wrapper.ApiWrapper`.
