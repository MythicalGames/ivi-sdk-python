import asyncio
import google.protobuf
import grpc
import pytest

import random

from ivi_sdk.ivi_client import IVIClient
from ivi_sdk.common.item.definition_pb2 import ItemState
from ivi_sdk.common.itemtype.definition_pb2 import ItemTypeState
from ivi_sdk.common.order.definition_pb2 import OrderState
from ivi_sdk.common.player.definition_pb2 import PlayerState
from ivi_sdk.streams.item.stream_pb2 import ItemStatusUpdate, ItemStatusConfirmRequest
from ivi_sdk.streams.item.stream_pb2_grpc import ItemStreamServicer, add_ItemStreamServicer_to_server
from ivi_sdk.streams.itemtype.stream_pb2 import ItemTypeStatusUpdate, ItemTypeStatusConfirmRequest
from ivi_sdk.streams.itemtype.stream_pb2_grpc import ItemTypeStatusStreamServicer, add_ItemTypeStatusStreamServicer_to_server
from ivi_sdk.streams.order.stream_pb2 import OrderStatusUpdate, OrderStatusConfirmRequest
from ivi_sdk.streams.order.stream_pb2_grpc import OrderStreamServicer, add_OrderStreamServicer_to_server
from ivi_sdk.streams.player.stream_pb2 import PlayerStatusUpdate, PlayerStatusConfirmRequest
from ivi_sdk.streams.player.stream_pb2_grpc import PlayerStreamServicer, add_PlayerStreamServicer_to_server

def random_string(length:int):
    from string import ascii_letters, digits
    chars = ascii_letters+digits
    return ''.join(random.choice(chars) for i in range(length))

def item_update(msg:ItemStatusUpdate):
    pass

def itemtype_update(msg:ItemTypeStatusUpdate):
    pass

def order_update(msg:OrderStatusUpdate):
    pass

def player_updated(msg:PlayerStatusUpdate):
    pass

ivi_envid = random_string(12)
num_messages = 1000
listen_port = str(random.randrange(16000, 30000))

class FakeItemStreamServicerImpl(ItemStreamServicer):

    def __init__(self):
        self.updates = {}
        self.confirms = []
        self.complete = asyncio.Event()
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
        assert request.environment_id == ivi_envid
        for uid, update in self.updates.items():
            yield update


    async def ItemStatusConfirmation(self, request, context):
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
        self.updates = {}
        self.confirms = []
        self.complete = asyncio.Event()
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
        assert request.environment_id == ivi_envid
        for uid, update in self.updates.items():
            yield update


    async def ItemTypeStatusConfirmation(self, request, context):
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
        self.updates = {}
        self.confirms = []
        self.complete = asyncio.Event()
        for i in range(0, int(num_messages/2)):
            uid = random_string(10)
            self.updates[uid] = OrderStatusUpdate(
                order_id=uid)
            uid = random_string(10)
            self.updates[uid] = OrderStatusUpdate(
                order_id=uid,
                order_state=random.choice(OrderState.values()))

    async def OrderStatusStream(self, request, context):
        assert request.environment_id == ivi_envid
        for uid, update in self.updates.items():
            yield update


    async def OrderStatusConfirmation(self, request, context):
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
        self.updates = {}
        self.confirms = []
        self.complete = asyncio.Event()
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
        assert request.environment_id == ivi_envid
        for uid, update in self.updates.items():
            yield update


    async def PlayerStatusConfirmation(self, request, context):
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
async def test_client():

    assert num_messages % 2 == 0
    server = await run_server()
    
    item_stream_service = FakeItemStreamServicerImpl()
    item_type_stream_service = FakeItemTypeStreamServicerImpl()
    order_stream_service = FakeOrderStreamServicerImpl()
    player_stream_service = FakePlayerStreamServicerImpl()
    
    add_ItemStreamServicer_to_server(item_stream_service, server)
    add_ItemTypeStatusStreamServicer_to_server(item_type_stream_service, server)
    add_OrderStreamServicer_to_server(order_stream_service, server)
    add_PlayerStreamServicer_to_server(player_stream_service, server)
    
    ivi_server = 'localhost:' + listen_port
    async with grpc.aio.insecure_channel(ivi_server) as channel:
        ivi_client = IVIClient(ivi_server, ivi_envid, random_string(64),
                        item_update, itemtype_update, order_update, player_updated,
                        channel = channel)
        
        assert ivi_client.item_service is not None
        assert ivi_client.itemtype_service is not None
        assert ivi_client.order_service is not None
        assert ivi_client.payment_service is not None
        assert ivi_client.player_service is not None
        
        [asyncio.ensure_future(coro()) for coro in ivi_client.coroutines()]

        await asyncio.wait_for(item_stream_service.complete.wait(), timeout=10)
        await asyncio.wait_for(item_type_stream_service.complete.wait(), timeout=10)
        await asyncio.wait_for(order_stream_service.complete.wait(), timeout=10)
        await asyncio.wait_for(player_stream_service.complete.wait(), timeout=10)
        
        await ivi_client.close()
        await server.stop(1.0)
        
        assert num_messages == len(item_stream_service.confirms)
        assert len(item_stream_service.updates) == len(item_stream_service.confirms)

        assert num_messages == len(item_type_stream_service.confirms)
        assert len(item_type_stream_service.updates) == len(item_type_stream_service.confirms)

        assert num_messages == len(order_stream_service.confirms)
        assert len(order_stream_service.updates) == len(order_stream_service.confirms)

        assert num_messages == len(player_stream_service.confirms)
        assert len(player_stream_service.updates) == len(player_stream_service.confirms)
