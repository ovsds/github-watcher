import typing

import aiohttp
import pytest_asyncio

import lib.telegram.clients as telegram_clients
import tests.settings as test_settings


@pytest_asyncio.fixture(name="aiohttp_client")
async def aiohttp_client_fixture() -> typing.AsyncGenerator[aiohttp.ClientSession, None]:
    client = aiohttp.ClientSession()
    try:
        yield client
    finally:
        await client.close()


@pytest_asyncio.fixture(name="telegram_client")
async def telegram_client_fixture(
    aiohttp_client: aiohttp.ClientSession,
    settings: test_settings.Settings,
) -> telegram_clients.RestTelegramClient:
    return telegram_clients.RestTelegramClient(
        token=settings.telegram_token,
        aiohttp_client=aiohttp_client,
    )
