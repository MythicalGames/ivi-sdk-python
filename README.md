# IVI Python SDK

## General info
The *IVI Python SDK* is a minimal wrapper layer around the underlying [IVI gRPC Streams API](https://github.com/MythicalGames/ivi-sdk-proto/).  The primary module is `ivi_sdk/ivi_client.py`.

The SDK is installable via `pip` and should be usable with any released Python >= 3.6.  The included `setup.py` will download, generate, and install the necessary gRPC and protobuf dependencies, as well as fetch protos and run the `protoc` code generator.

The `IVIClient` makes use of `asyncio` and `grpc.aio` for managing stream processing via coroutines, and also instantiates the unary RPC stubs for convenience.  This SDK does *not* wrap the unary RPC calls - users should refer directly to the proto files and interact directly with the generated protobuf and gRPC Python code for unary calls as documented in the Readme.io guide.  Examples are available there as well as in `tests/example.py`.  However, unlike the example code, it is strongly recommend for users to schedule any unary RPC calls and processing within their own coroutine wrappers, to avoid stalling the main Python thread.

It is strongly suggested to set the `asycio` event loop global exception handler via [`set_exception_handler`](https://docs.python.org/3/library/asyncio-eventloop.html#id15) and fixing or reporting any errors found therein.  Failing to do so may lead to memory leaks through unbounded accumulation of unhandled errors.

`pytest` based unit tests for the `IVIClient` stream processing are contained in `tests/test_ivi_client.py` script.  This will also require the `pytest-asyncio` package to be installed.

Recommended further reading beyond the RPC guide:
* [asyncio](https://docs.python.org/3/library/asyncio.html)
* [protobuf generated code](https://developers.google.com/protocol-buffers/docs/reference/python-generated)
* [gRPC Python](https://grpc.io/docs/languages/python/) and [gRPC AsyncIO](https://grpc.github.io/grpc/python/grpc_asyncio.html)
