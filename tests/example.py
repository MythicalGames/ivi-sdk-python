#!/usr/bin/env python3
"""
Example script for registering callbacks and calling API functions through
the ivi_sdk ivi_client.
Usage:
    example.py <server> <envid> <apikey> [sleep_loop_seconds] [num_loops]
"""

import asyncio
import logging
import os
import sys
import traceback
import grpc
from ivi_sdk.ivi_client import IVIClient
from ivi_sdk.streams.item.stream_pb2 import ItemStatusUpdate
from ivi_sdk.streams.itemtype.stream_pb2 import ItemTypeStatusUpdate
from ivi_sdk.streams.order.stream_pb2 import OrderStatusUpdate
from ivi_sdk.streams.player.stream_pb2 import PlayerStatusUpdate


def random_string(length: int):
    from random import choice
    from string import ascii_letters
    from string import digits
    chars = ascii_letters+digits
    return ''.join(choice(chars) for i in range(length))


def item_update(msg: ItemStatusUpdate):
    print('Item Status Update received\n', msg)


def itemtype_update(msg: ItemTypeStatusUpdate):
    print('ItemType Status Update received\n', msg)


def order_update(msg: OrderStatusUpdate):
    print('Order Status Update received\n', msg)


def player_updated(msg: PlayerStatusUpdate):
    print('Player Status Update received\n', msg)


async def run(ivi_client: IVIClient, sleep_for: int = 60, max_loop: int = 2):
    issued_item_count = 0
    argc = len(sys.argv)
    if argc >= 5:
        sleep_for = int(sys.argv[4])
    if argc >= 6:
        max_loop = int(sys.argv[5])
    print('Will issue', max_loop, 'items, sleeping between each issue for',
          sleep_for,
          'seconds, then terminating for issuing one too many items')
    try:
        # These examples await results of RPC calls, which you may or may not
        # want to do depending on your program's requirements and threading
        # structure.  In most cases, you will likely instead want to wrap each
        # RPC in an async function which includes your own logic for
        # processing the result, and add it to your preferred event loop.
        import uuid
        from ivi_sdk.api.item.definition_pb2 import IssueItemRequest
        from ivi_sdk.api.itemtype.definition_pb2 import CreateItemTypeRequest
        from ivi_sdk.api.player.definition_pb2 import LinkPlayerRequest

        # create an itemtype and a player
        create_itemtype_request = CreateItemTypeRequest(
            environment_id=ivi_client.envid,
            token_name='test name ' + random_string(4),
            category='test category',
            max_supply=max_loop,
            issue_time_span=0,
            burnable=True,
            transferable=True,
            sellable=True,
            game_item_type_id=random_string(16))
        create_itemtype_request.metadata.name = 'an item type'
        create_itemtype_request.metadata.description = 'a description'
        create_itemtype_request.metadata.image = 'https://a.url'
        create_itemtype_request.metadata.properties.update({'foo': 'bar'})
        create_itemtype_response = await (
            ivi_client.itemtype_service.CreateItemType(
                create_itemtype_request))
        print('Item Type created:')
        print(create_itemtype_response)

        # now just loop making players and issuing items till we hit
        # max_supply hard coded above, which raises the below-caught exception
        while True:

            link_player_request = LinkPlayerRequest(
                environment_id=ivi_client.envid,
                player_id=random_string(12),
                email='{}@{}.com'.format(random_string(4), random_string(5)),
                display_name=random_string(2),
                request_ip='127.0.0.1')
            link_player_response = await ivi_client.player_service.LinkPlayer(
                link_player_request)
            print('Player linked:')
            print(link_player_response)

            issue_item_request = IssueItemRequest(
                environment_id=ivi_client.envid,
                game_inventory_id=random_string(12),
                player_id=link_player_request.player_id,
                item_name='test item name',
                game_item_type_id=create_itemtype_response.game_item_type_id,
                amount_paid='1.00',
                currency='USD',
                store_id='test',
                order_id=str(uuid.uuid4()),
                request_ip='127.0.0.1')
            issue_item_request.metadata.name = 'an item'
            issue_item_request.metadata.description = 'another description'
            issue_item_request.metadata.image = 'https://another.url'
            issue_item_request.metadata.properties.update({'Alice': 'Bob'})
            issue_item_response = await (
                ivi_client.item_service.IssueItem(issue_item_request))
            print('Item issued:')
            print(issue_item_response)

            issued_item_count += 1
            print('sleeping...')
            await asyncio.sleep(sleep_for)

    except grpc.aio.AioRpcError as e:
        if (issued_item_count == max_loop and e.code() ==
           grpc.StatusCode.FAILED_PRECONDITION):
            print('\nExample IssueItem loop complete, here is the expected '
                  'Exception from issuing one too many of an '
                  'ItemType:\n\n', e)
        else:
            print('Unexpected AioRpcError in the example program')
            traceback.print_exc()
    except Exception:
        print('Unknown Exception')
        traceback.print_exc()
    finally:
        print('Closing...')


def handle_exception(loop, context):
    global global_exception_handler_hit
    global_exception_handler_hit = True
    print('UNHANDLED asyncio exception - this is a bug!')
    if context is not None:
        if 'message' in context:
            print(context['message'])
            print(context['exception'])
        else:
            print('No message?')
            print(context)
    else:
        print('no context supplied')
    traceback.print_exc()


async def main(
    ivi_server: str = None,
    ivi_envid: str = None,
    ivi_apikey: str = None
):
    """
    Run the asyncio-based gRPC ivi_client
    """
    logging.basicConfig()

    if ivi_server is None or ivi_envid is None or ivi_apikey is None:
        raise RuntimeError('Usage: <server> <envid> <apikey> '
                           '[sleep_loop_seconds] [num_loops]')

    if ivi_server == IVIClient.default_host:
        raise RuntimeError('Please do not run the example program '
                           'against the production server')

    # global exception handler
    asyncio.get_event_loop().set_exception_handler(handle_exception)

    # initialize the ivi_client, we can use async with or explicitly
    # call ivi_client.close() when done
    async with IVIClient(ivi_server, ivi_envid, ivi_apikey,
                         item_update, itemtype_update, order_update,
                         player_updated) as ivi_client:

        # required - stream updates need confirmation messages sent
        # back to the server exact scheduling semantics are left up to
        # sdk users
        [asyncio.ensure_future(coro()) for coro in ivi_client.coroutines()]

        # kick off our example API calls which will push stream updates
        # back to us
        await run(ivi_client)


if __name__ == '__main__':
    argc = len(sys.argv)
    ivi_server = os.getenv('IVI_HOST') if argc < 2 else sys.argv[1]
    ivi_envid = os.getenv('IVI_ENV_ID') if argc < 3 else sys.argv[2]
    ivi_apikey = os.getenv('IVI_API_KEY') if argc < 4 else sys.argv[3]

    global global_exception_handler_hit
    global_exception_handler_hit = False
    asyncio.get_event_loop().run_until_complete(
        main(ivi_server=ivi_server,
             ivi_envid=ivi_envid,
             ivi_apikey=ivi_apikey))
    if global_exception_handler_hit:
        print('Finished but unhandled error detected')
        sys.exit(1)  # report the error to any testing scripts
    print('Finished!')
