Clients
=======

When you implement an agent for the AI System Project, it will need to communicate with the server.
A client is a program that sends requests to the server and processes the responses.
The client can be implemented in any programming language.
However, we provide client implementations that you can just use,
so that you don't have to deal with the details of the protocol.
If you want to use a different programming language,
you can use the provided implementations as a reference.



Client implementations
----------------------

* `"Standard" Python client <https://github.com/jfschaefer/aisysprojserver/blob/main/aisysprojserver_clienttools/client.py>`_
* `Simple Python client (for protocol version 0) <https://github.com/jfschaefer/aisysprojserver/blob/main/aisysprojserver_clienttools/client_simple_v0.py>`_
* `Simple Python client (for protocol version 1) <https://github.com/jfschaefer/aisysprojserver/blob/main/aisysprojserver_clienttools/client_simple_v1.py>`_



Server protocol
---------------

The client-server-protocol is based on HTTP requests and responses.
The client sends an HTTP request to the server with the credentials,
and the server responds with a list of action requests.
The client then sends another request with the actions for the server,
which responds with new action requests.

Currently, there are two versions of the protocol:

* `Version 0 <server_protocol_v0.html>`_
* `Version 1 <server_protocol_v1.html>`_

It is recommended to use the latest version of the protocol.
Older versions are still supported, but might be deprecated in the future.
