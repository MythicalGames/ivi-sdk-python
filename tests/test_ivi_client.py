import asyncio
import google.protobuf
import grpc
import pytest
import random
from ivi_sdk.ivi_client import IVIClient
from ivi_sdk.api.item.rpc_pb2_grpc import ItemServiceStub
from ivi_sdk.api.item.definition_pb2 import IssueItemRequest
from ivi_sdk.common.item.definition_pb2 import ItemState
from ivi_sdk.common.itemtype.definition_pb2 import ItemTypeState
from ivi_sdk.common.order.definition_pb2 import OrderState
from ivi_sdk.common.player.definition_pb2 import PlayerState
from ivi_sdk.streams.item.stream_pb2 import ItemStatusUpdate
from ivi_sdk.streams.item.stream_pb2_grpc import (
    ItemStreamServicer,
    add_ItemStreamServicer_to_server)
from ivi_sdk.streams.itemtype.stream_pb2 import ItemTypeStatusUpdate
from ivi_sdk.streams.itemtype.stream_pb2_grpc import (
    ItemTypeStatusStreamServicer,
    add_ItemTypeStatusStreamServicer_to_server)
from ivi_sdk.streams.order.stream_pb2 import OrderStatusUpdate
from ivi_sdk.streams.order.stream_pb2_grpc import (
    OrderStreamServicer,
    add_OrderStreamServicer_to_server)
from ivi_sdk.streams.player.stream_pb2 import PlayerStatusUpdate
from ivi_sdk.streams.player.stream_pb2_grpc import (
    PlayerStreamServicer,
    add_PlayerStreamServicer_to_server)


def random_string(length: int):
    from string import ascii_letters, digits
    chars = ascii_letters+digits
    return ''.join(random.choice(chars) for i in range(length))


class UpdateReceiver:
    def __init__(self):
        self.num_item_update_calls = 0
        self.num_itemtype_update_calls = 0
        self.num_order_update_calls = 0
        self.num_player_update_calls = 0

    def item_update(self, msg: ItemStatusUpdate):
        self.num_item_update_calls += 1

    def itemtype_update(self, msg: ItemTypeStatusUpdate):
        self.num_itemtype_update_calls += 1

    def order_update(self, msg: OrderStatusUpdate):
        self.num_order_update_calls += 1

    def player_updated(self, msg: PlayerStatusUpdate):
        self.num_player_update_calls += 1


ivi_envid = random_string(12)
num_messages = 1000
listen_port = str(random.randrange(16000, 30000))


class FakeItemStreamServicerImpl(ItemStreamServicer):

    def __init__(self):
        self.raise_error = True
        self.confirm_count = 0
        self.updates = {}
        self.confirms = []
        self.complete = asyncio.Event()
        self.terminate_stream = asyncio.Event()
        for i in range(0, int(num_messages/2)):
            uid = random_string(10)
            self.updates[uid] = ItemStatusUpdate(
                game_inventory_id=uid,
                tracking_id=random_string(12))
            uid = random_string(10)
            self.updates[uid] = ItemStatusUpdate(
                game_inventory_id=uid,
                tracking_id=random_string(12),
                item_state=random.choice(ItemState.values()))

    async def ItemStatusStream(self, request, context):
        if self.raise_error:
            self.raise_error = False
            await context.abort(
                grpc.StatusCode.INTERNAL,
                'Received RST_STREAM with error code 2')
        else:
            assert request.environment_id == ivi_envid
            for uid, update in self.updates.items():
                yield update
            await self.terminate_stream.wait()

    async def ItemStatusConfirmation(self, request, context):
        self.confirm_count += 1
        assert request.game_inventory_id in self.updates
        assert request.game_inventory_id not in self.confirms
        update = self.updates[request.game_inventory_id]
        assert update.tracking_id == request.tracking_id
        assert update.item_state == request.item_state
        assert ivi_envid == request.environment_id
        self.confirms.append(request.game_inventory_id)
        if len(self.confirms) == num_messages:
            self.complete.set()
        return google.protobuf.empty_pb2.Empty()


class FakeItemTypeStreamServicerImpl(ItemTypeStatusStreamServicer):

    def __init__(self):
        self.raise_error = True
        self.confirm_count = 0
        self.updates = {}
        self.confirms = []
        self.complete = asyncio.Event()
        self.terminate_stream = asyncio.Event()
        for i in range(0, int(num_messages/2)):
            uid = random_string(10)
            self.updates[uid] = ItemTypeStatusUpdate(
                game_item_type_id=uid,
                tracking_id=random_string(12))
            uid = random_string(10)
            self.updates[uid] = ItemTypeStatusUpdate(
                game_item_type_id=uid,
                tracking_id=random_string(12),
                item_type_state=random.choice(ItemTypeState.values()))

    async def ItemTypeStatusStream(self, request, context):
        if self.raise_error:
            self.raise_error = False
            await context.abort(
                grpc.StatusCode.UNKNOWN,
                'Received http2 header with status: 524')
        else:
            assert request.environment_id == ivi_envid
            for uid, update in self.updates.items():
                yield update
            await self.terminate_stream.wait()

    async def ItemTypeStatusConfirmation(self, request, context):
        self.confirm_count += 1
        assert request.game_item_type_id in self.updates
        assert request.game_item_type_id not in self.confirms
        update = self.updates[request.game_item_type_id]
        assert update.tracking_id == request.tracking_id
        assert update.item_type_state == request.item_type_state
        assert ivi_envid == request.environment_id
        self.confirms.append(request.game_item_type_id)
        if len(self.confirms) == num_messages:
            self.complete.set()
        return google.protobuf.empty_pb2.Empty()


class FakeOrderStreamServicerImpl(OrderStreamServicer):

    def __init__(self):
        self.raise_error = True
        self.confirm_count = 0
        self.updates = {}
        self.confirms = []
        self.complete = asyncio.Event()
        self.terminate_stream = asyncio.Event()
        for i in range(0, int(num_messages/2)):
            uid = random_string(10)
            self.updates[uid] = OrderStatusUpdate(
                order_id=uid)
            uid = random_string(10)
            self.updates[uid] = OrderStatusUpdate(
                order_id=uid,
                order_state=random.choice(OrderState.values()))

    async def OrderStatusStream(self, request, context):
        if self.raise_error:
            self.raise_error = False
            await context.abort(grpc.StatusCode.NOT_FOUND)
        else:
            assert request.environment_id == ivi_envid
            for uid, update in self.updates.items():
                yield update
            await self.terminate_stream.wait()

    async def OrderStatusConfirmation(self, request, context):
        self.confirm_count += 1
        assert request.order_id in self.updates
        assert request.order_id not in self.confirms
        update = self.updates[request.order_id]
        assert update.order_state == request.order_state
        assert ivi_envid == request.environment_id
        self.confirms.append(request.order_id)
        if len(self.confirms) == num_messages:
            self.complete.set()
        return google.protobuf.empty_pb2.Empty()


class FakePlayerStreamServicerImpl(PlayerStreamServicer):

    def __init__(self):
        self.raise_error = True
        self.confirm_count = 0
        self.updates = {}
        self.confirms = []
        self.complete = asyncio.Event()
        self.terminate_stream = asyncio.Event()
        for i in range(0, int(num_messages/2)):
            uid = random_string(10)
            self.updates[uid] = PlayerStatusUpdate(
                player_id=uid,
                tracking_id=random_string(12))
            uid = random_string(10)
            self.updates[uid] = PlayerStatusUpdate(
                player_id=uid,
                tracking_id=random_string(12),
                player_state=random.choice(PlayerState.values()))

    async def PlayerStatusStream(self, request, context):
        if self.raise_error:
            self.raise_error = False
            await context.abort(grpc.StatusCode.UNAUTHENTICATED)
        else:
            assert request.environment_id == ivi_envid
            for uid, update in self.updates.items():
                yield update
            await self.terminate_stream.wait()

    async def PlayerStatusConfirmation(self, request, context):
        self.confirm_count += 1
        assert request.player_id in self.updates
        assert request.player_id not in self.confirms
        update = self.updates[request.player_id]
        assert update.tracking_id == request.tracking_id
        assert update.player_state == request.player_state
        assert ivi_envid == request.environment_id
        self.confirms.append(request.player_id)
        if len(self.confirms) == num_messages:
            self.complete.set()
        return google.protobuf.empty_pb2.Empty()


async def run_server() -> None:
    server = grpc.aio.server()
    server.add_insecure_port('[::]:' + listen_port)
    await server.start()
    return server


@pytest.mark.asyncio
async def test_client(event_loop):

    # pytest-asyncio will not automatically report & fail unhandled errors
    def handle_async_exception(loop, ctx):
        pytest.fail("Exception in async task: {0}".format(ctx['exception']))
    event_loop.set_exception_handler(handle_async_exception)

    assert num_messages % 2 == 0
    server = await run_server()
    item_stream_service = FakeItemStreamServicerImpl()
    item_type_stream_service = FakeItemTypeStreamServicerImpl()
    order_stream_service = FakeOrderStreamServicerImpl()
    player_stream_service = FakePlayerStreamServicerImpl()
    add_ItemStreamServicer_to_server(item_stream_service, server)
    add_ItemTypeStatusStreamServicer_to_server(
        item_type_stream_service, server)
    add_OrderStreamServicer_to_server(
        order_stream_service, server)
    add_PlayerStreamServicer_to_server(
        player_stream_service, server)
    ivi_server = 'localhost:' + listen_port
    async with grpc.aio.insecure_channel(ivi_server) as channel:
        receiver = UpdateReceiver()
        ivi_client = IVIClient(
                        ivi_server,
                        ivi_envid,
                        random_string(64),
                        receiver.item_update,
                        receiver.itemtype_update,
                        receiver.order_update,
                        receiver.player_updated,
                        channel=channel)
        assert ivi_client.item_service is not None
        assert ivi_client.itemtype_service is not None
        assert ivi_client.order_service is not None
        assert ivi_client.payment_service is not None
        assert ivi_client.player_service is not None
        [asyncio.ensure_future(coro()) for coro in ivi_client.coroutines()]
        await asyncio.wait_for(
            item_stream_service.complete.wait(),
            timeout=10)
        await asyncio.wait_for(
            item_type_stream_service.complete.wait(),
            timeout=10)
        await asyncio.wait_for(
            order_stream_service.complete.wait(),
            timeout=10)
        await asyncio.wait_for(
            player_stream_service.complete.wait(),
            timeout=10)

        # Message count sanity check
        assert num_messages == len(item_stream_service.updates)
        assert num_messages == len(item_type_stream_service.updates)
        assert num_messages == len(order_stream_service.updates)
        assert num_messages == len(player_stream_service.updates)
        # Callbacks
        assert num_messages == receiver.num_item_update_calls
        assert num_messages == receiver.num_itemtype_update_calls
        assert num_messages == receiver.num_order_update_calls
        assert num_messages == receiver.num_player_update_calls
        # Confirm messages received
        assert num_messages == item_stream_service.confirm_count
        assert num_messages == item_type_stream_service.confirm_count
        assert num_messages == order_stream_service.confirm_count
        assert num_messages == player_stream_service.confirm_count
        # Confirm messages properly confirmed
        assert num_messages == len(item_stream_service.confirms)
        assert num_messages == len(item_type_stream_service.confirms)
        assert num_messages == len(order_stream_service.confirms)
        assert num_messages == len(player_stream_service.confirms)

        await ivi_client.close()
        item_stream_service.terminate_stream.set()
        item_type_stream_service.terminate_stream.set()
        order_stream_service.terminate_stream.set()
        player_stream_service.terminate_stream.set()
        await server.stop(1.0)

        # ensure channel closure
        try:
            item_service = ItemServiceStub(channel)
            await item_service.IssueItem(IssueItemRequest())
            assert False
        except grpc.aio.UsageError:
            pass


@pytest.mark.asyncio
async def test_client_async_with(event_loop):

    # pytest-asyncio will not automatically report & fail unhandled errors
    def handle_async_exception(loop, ctx):
        pytest.fail("Exception in async task: {0}".format(ctx['exception']))
    event_loop.set_exception_handler(handle_async_exception)

    assert num_messages % 2 == 0
    server = await run_server()
    item_stream_service = FakeItemStreamServicerImpl()
    item_type_stream_service = FakeItemTypeStreamServicerImpl()
    order_stream_service = FakeOrderStreamServicerImpl()
    player_stream_service = FakePlayerStreamServicerImpl()
    add_ItemStreamServicer_to_server(item_stream_service, server)
    add_ItemTypeStatusStreamServicer_to_server(
        item_type_stream_service, server)
    add_OrderStreamServicer_to_server(
        order_stream_service, server)
    add_PlayerStreamServicer_to_server(
        player_stream_service, server)
    ivi_server = 'localhost:' + listen_port
    receiver = UpdateReceiver()
    async with grpc.aio.insecure_channel(ivi_server) as channel:
        async with IVIClient(ivi_server,
                             ivi_envid,
                             random_string(64),
                             receiver.item_update,
                             receiver.itemtype_update,
                             receiver.order_update,
                             receiver.player_updated,
                             channel=channel) as ivi_client:
            assert ivi_client.item_service is not None
            assert ivi_client.itemtype_service is not None
            assert ivi_client.order_service is not None
            assert ivi_client.payment_service is not None
            assert ivi_client.player_service is not None
            [asyncio.ensure_future(coro())
                for coro in ivi_client.coroutines()]
            await asyncio.wait_for(
                item_stream_service.complete.wait(),
                timeout=10)
            await asyncio.wait_for(
                item_type_stream_service.complete.wait(),
                timeout=10)
            await asyncio.wait_for(
                order_stream_service.complete.wait(),
                timeout=10)
            await asyncio.wait_for(
                player_stream_service.complete.wait(),
                timeout=10)

        # ensure channel closure
        try:
            item_service = ItemServiceStub(channel)
            await item_service.IssueItem(IssueItemRequest())
            assert False
        except grpc.aio.UsageError:
            pass

    # Message count sanity check
    assert num_messages == len(item_stream_service.updates)
    assert num_messages == len(item_type_stream_service.updates)
    assert num_messages == len(order_stream_service.updates)
    assert num_messages == len(player_stream_service.updates)
    # Callbacks
    assert num_messages == receiver.num_item_update_calls
    assert num_messages == receiver.num_itemtype_update_calls
    assert num_messages == receiver.num_order_update_calls
    assert num_messages == receiver.num_player_update_calls
    # Confirm messages received
    assert num_messages == item_stream_service.confirm_count
    assert num_messages == item_type_stream_service.confirm_count
    assert num_messages == order_stream_service.confirm_count
    assert num_messages == player_stream_service.confirm_count
    # Confirm messages properly confirmed
    assert num_messages == len(item_stream_service.confirms)
    assert num_messages == len(item_type_stream_service.confirms)
    assert num_messages == len(order_stream_service.confirms)
    assert num_messages == len(player_stream_service.confirms)

    item_stream_service.terminate_stream.set()
    item_type_stream_service.terminate_stream.set()
    order_stream_service.terminate_stream.set()
    player_stream_service.terminate_stream.set()
    await server.stop(1.0)
