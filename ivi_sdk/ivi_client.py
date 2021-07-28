import logging
from typing import Any, Callable, List, Tuple

import asyncio
import grpc
import grpc.aio

from ivi_sdk.api.item.rpc_pb2_grpc import ItemServiceStub
from ivi_sdk.api.itemtype.rpc_pb2_grpc import ItemTypeServiceStub
from ivi_sdk.api.order.rpc_pb2_grpc import OrderServiceStub
from ivi_sdk.api.payment.rpc_pb2_grpc import PaymentServiceStub
from ivi_sdk.api.player.rpc_pb2_grpc import PlayerServiceStub
from ivi_sdk.streams.common_pb2 import Subscribe as IVISubscribeRequest
from ivi_sdk.streams.item.stream_pb2 import ItemStatusUpdate
from ivi_sdk.streams.item.stream_pb2 import ItemStatusConfirmRequest
from ivi_sdk.streams.item.stream_pb2_grpc import ItemStreamStub
from ivi_sdk.streams.itemtype.stream_pb2 import ItemTypeStatusUpdate
from ivi_sdk.streams.itemtype.stream_pb2 import ItemTypeStatusConfirmRequest
from ivi_sdk.streams.itemtype.stream_pb2_grpc import ItemTypeStatusStreamStub
from ivi_sdk.streams.order.stream_pb2 import OrderStatusUpdate
from ivi_sdk.streams.order.stream_pb2 import OrderStatusConfirmRequest
from ivi_sdk.streams.order.stream_pb2_grpc import OrderStreamStub
from ivi_sdk.streams.player.stream_pb2 import PlayerStatusUpdate
from ivi_sdk.streams.player.stream_pb2 import PlayerStatusConfirmRequest
from ivi_sdk.streams.player.stream_pb2_grpc import PlayerStreamStub


class IVIClient:
    """
    A simple, thin wrapper and management layer for the IVI protobuf
    & gRPC API.
    Refer to the .proto files and online documentation for detailed API
    usage information, as well as protobuf & gRPC documentation.

    This class supports `async with` semantics, otherwise remember to call
    close() when done.

    This class is not thread-safe and should be instanced 1-per-thread.

    Attributes
    ----------
    channel : grpc.aio.Channel
    envid : str
    item_service : ItemServiceStub
        from ivi_sdk.api.item.rpc_pb2_grpc
    itemtype_service : ItemTypeServiceStub
        from ivi_sdk.api.itemtype.rpc_pb2_grpc
    order_service : OrderServiceStub
        from ivi_sdk.api.order.rpc_pb2_grpc
    payment_service : PaymentServiceStub
        from ivi_sdk.api.payment.rpc_pb2_grpc
    player_service : PlayerServiceStub
        from ivi_sdk.api.player.rpc_pb2_grpc
    default_host : str
        The production IVI endpoint
    channel_options : List of tuples
        Default options passed to the underlying gRPC channel
    default_sleep_on_cloudflare_error : int
        Default amount of time to wait after a Cloudflare timeout
    Methods
    -------
    coroutines()
        Returns a tuple of the coroutines which should be scheduled
        with asyncio and will run until close() is called.
        Eg in Python 3.6:
        [asyncio.ensure_future(coro()) for coro inivi_client.coroutines()]
        The coroutines will execute the callbacks and, unless an Exception is
        raised, will send a confirmation message back to the IVI host.
        The coroutines will log and continue after catching an Exception - if
        you desire different behavior, don't let the Exception from your
        callback bubble.
    close()
        Cancels the RPC streams which lead to callback execution and closes
        the underlying channel.
    """

    default_host = 'sdk-api.iviengine.com:443'
    default_channel_options = [('grpc.keepalive_time_ms', 30 * 1000)]
    default_sleep_on_cloudflare_error = 1

    def __init__(
        self,
        host: str,
        envid: str,
        apikey: str,
        on_item_status_update: Callable[[ItemStatusUpdate], None],
        on_itemtype_status_update: Callable[[ItemTypeStatusUpdate], None],
        on_order_status_update: Callable[[OrderStatusUpdate], None],
        on_player_status_update: Callable[[PlayerStatusUpdate], None],
        channel_options: List[Tuple[str, Any]] = default_channel_options,
        channel: grpc.aio.Channel = None
    ):
        """
        Parameters
        ----------
        host : str
            Server endpoint.  The production server is given by the class
            attribute default_host
        envid : str
            Environment id for your product / account
        apikey : str
            The api-key for your product / account
        on_item_status_update : callable(ItemStatusUpdate)
            Called when an ItemStatusUpdate from
            ivi_sdk.streams.item.stream_pb2 is received
        on_itemtype_status_update : callable(ItemTypeStatusUpdate)
            Called when an ItemTypeStatusUpdate from
            ivi_sdk.streams.itemtype.stream_pb2 is received
        on_order_status_update : callable(OrderStatusUpdate)
            Called when an OrderStatusUpdate from
            ivi_sdk.streams.order.stream_pb2 is received
        on_player_status_update : callable(PlayerStatusUpdate)
            Called when a PlayerStatusUpdate from
            ivi_sdk.streams.player.stream_pb2 is received
        channel_options : List of tuples
            Custom gRPC options
        channel : Already-instantiated gRPC channel.
        """

        if channel is None:
            ssl_credentials = grpc.ssl_channel_credentials()
            metadata_credentials = grpc.metadata_call_credentials(
                self._IVIMetadataPlugin(apikey))
            self.channel = grpc.aio.secure_channel(
                target=host,
                credentials=grpc.composite_channel_credentials(
                    ssl_credentials,
                    metadata_credentials),
                options=channel_options)
        else:
            self.channel = channel

        self.envid = envid

        self._on_item_status_update = on_item_status_update
        self._on_itemtype_status_update = on_itemtype_status_update
        self._on_order_status_update = on_order_status_update
        self._on_player_status_update = on_player_status_update

        self.item_service = ItemServiceStub(self.channel)
        self.itemtype_service = ItemTypeServiceStub(self.channel)
        self.order_service = OrderServiceStub(self.channel)
        self.payment_service = PaymentServiceStub(self.channel)
        self.player_service = PlayerServiceStub(self.channel)

        self._item_stream = ItemStreamStub(self.channel)
        self._itemtype_stream = ItemTypeStatusStreamStub(self.channel)
        self._order_stream = OrderStreamStub(self.channel)
        self._player_stream = PlayerStreamStub(self.channel)

        self._closed = False

    async def __aenter__(self):
        """
        await underlying network connection to ready, or raise
        """
        await self.channel.channel_ready()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """
        await underlying network connection to shutdown
        """
        if exc is not None:
            logging.exception(exc)
        await self.close()

    async def _handle_stream_excepton(self, exc):
        if ((exc.code() == grpc.StatusCode.UNKNOWN
                and exc.details() is not None
                and exc.details() ==
                'Received http2 header with status: 524')
            or
            (exc.code() == grpc.StatusCode.INTERNAL
                and exc.details() is not None
                and exc.details() ==
                'Received RST_STREAM with error code 2')):
            logging.info('Cloudflare timeout (expected), moving on')
            await asyncio.sleep(self.default_sleep_on_cloudflare_error)
        else:
            logging.exception(exc)

    async def _item_coroutine(self) -> None:
        while not self._closed:
            self._item_status_stream_it = (
                self._item_stream.ItemStatusStream(
                    IVISubscribeRequest(environment_id=self.envid)))
            try:
                async for update in self._item_status_stream_it:
                    try:
                        self._on_item_status_update(update)
                        self._item_stream.ItemStatusConfirmation(
                            ItemStatusConfirmRequest(
                                environment_id=self.envid,
                                game_inventory_id=update.game_inventory_id,
                                tracking_id=update.tracking_id,
                                item_state=update.item_state))
                    except Exception as e:
                        logging.exception(e)
            except grpc.aio.AioRpcError as e:
                await self._handle_stream_excepton(e)
            except Exception as e:
                logging.exception(e)
            finally:
                self._item_status_stream_it.cancel()

    async def _itemtype_coroutine(self) -> None:
        while not self._closed:
            self._itemtype_status_stream_it = (
                self._itemtype_stream.ItemTypeStatusStream(
                    IVISubscribeRequest(environment_id=self.envid)))
            try:
                async for update in self._itemtype_status_stream_it:
                    try:
                        self._on_itemtype_status_update(update)
                        self._itemtype_stream.ItemTypeStatusConfirmation(
                            ItemTypeStatusConfirmRequest(
                                environment_id=self.envid,
                                game_item_type_id=update.game_item_type_id,
                                tracking_id=update.tracking_id,
                                item_type_state=update.item_type_state))
                    except Exception as e:
                        logging.exception(e)
            except grpc.aio.AioRpcError as e:
                await self._handle_stream_excepton(e)
            except Exception as e:
                logging.exception(e)
            finally:
                self._itemtype_status_stream_it.cancel()

    async def _order_coroutine(self) -> None:
        while not self._closed:
            self._order_status_stream_it = (
                self._order_stream.OrderStatusStream(
                    IVISubscribeRequest(environment_id=self.envid)))
            try:
                async for update in self._order_status_stream_it:
                    try:
                        self._on_order_status_update(update)
                        self._order_stream.OrderStatusConfirmation(
                            OrderStatusConfirmRequest(
                                environment_id=self.envid,
                                order_id=update.order_id,
                                order_state=update.order_state))
                    except Exception as e:
                        logging.exception(e)
            except grpc.aio.AioRpcError as e:
                await self._handle_stream_excepton(e)
            except Exception as e:
                logging.exception(e)
            finally:
                self._order_status_stream_it.cancel()

    async def _player_coroutine(self) -> None:
        while not self._closed:
            self._player_status_stream_it = (
                self._player_stream.PlayerStatusStream(
                    IVISubscribeRequest(environment_id=self.envid)))
            try:
                async for update in self._player_status_stream_it:
                    try:
                        self._on_player_status_update(update)
                        self._player_stream.PlayerStatusConfirmation(
                            PlayerStatusConfirmRequest(
                                environment_id=self.envid,
                                player_id=update.player_id,
                                tracking_id=update.tracking_id,
                                player_state=update.player_state))
                    except Exception as e:
                        logging.exception(e)
            except grpc.aio.AioRpcError as e:
                await self._handle_stream_excepton(e)
            except Exception as e:
                logging.exception(e)
            finally:
                self._player_status_stream_it.cancel()

    def coroutines(self):
        """
        Returns a tuple of the coroutines which should be scheduled
        with asyncio and will run until close() is called.
        Eg in Python 3.6:
        [asyncio.ensure_future(coro()) for coro inivi_client.coroutines()]
        The coroutines will execute the callbacks and, unless an Exception is
        raised, will send a confirmation message back to the IVI host.
        The coroutines will log and continue after catching an Exception - if
        you desire different behavior, don't let the Exception from your
        callback bubble.
        """
        return (self._item_coroutine,
                self._itemtype_coroutine,
                self._order_coroutine,
                self._player_coroutine)

    async def close(self):
        """
        Cancels the RPC streams which lead to callback execution and closes
        the underlying channel.

        """
        self._closed = True
        self._item_status_stream_it.cancel()
        self._itemtype_status_stream_it.cancel()
        self._order_status_stream_it.cancel()
        self._player_status_stream_it.cancel()
        await self.channel.close()

    class _IVIMetadataPlugin(grpc.AuthMetadataPlugin):
        """
        Internal adapter class for sending the api key as gRPC metadata to
        the server.
        """
        def __init__(self, apikey: str):
            self.ivi_apikey = apikey

        def __call__(self, context, callback):
            callback((('api-key', self.ivi_apikey),), None)
