# IVI Python SDK

## General info
The *IVI Python SDK* is a minimal wrapper layer around the underlying [IVI gRPC Streams API](https://github.com/MythicalGames/ivi-sdk-proto/).  All functionality is entirely contained in `ivi_sdk/ivi_client.py`.

It is installable via `pip` and should be usable with any released Python >= 3.6.  The included `setup.py` will install the necessary gRPC and protobuf dependencies, as well as fetch protos and run the `protoc` code generator.

The `IVIClient` makes use of `asyncio` and `grpc.aio` for managing stream processing via coroutines and also instantiates the unary RPC stubs for convenience.  This SDK does *not* wrap the unary RPC calls.  Users should interact directly with the generated gRPC Python code for unary calls as documented in the Readme.io guide.  Examples are available there as well as in `tests/example.py`.

It is strongly suggested to set the `asycio` event loop global exception handler via [`set_exception_handler`](https://docs.python.org/3/library/asyncio-eventloop.html#id15) and fixing or reporting any errors found therein.  Failing to do so may lead to memory leaks through unbounded accumulation of unhandled errors.

`pytest` based unit tests for the `IVIClient` stream processing are contained in `tests/test_ivi_client.py` script.  This will also require the `pytest-asyncio` package to be installed.

Recommended further reading beyond the RPC guide:
* [asyncio](https://docs.python.org/3/library/asyncio.html)
* [protobuf generated code](https://developers.google.com/protocol-buffers/docs/reference/python-generated)
* [gRPC Python](https://grpc.io/docs/languages/python/) and [gRPC AsyncIO](https://grpc.github.io/grpc/python/grpc_asyncio.html)
