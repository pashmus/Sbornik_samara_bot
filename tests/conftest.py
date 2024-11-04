import pytest
import pytest_asyncio
import asyncio
from aiogram import Dispatcher

from tests.mocked_bot import MockedBot


@pytest.fixture
def example_fixture():
    return "Hello, World!"


@pytest.fixture()
def bot():
    return MockedBot()


@pytest_asyncio.fixture()
async def dispatcher():
    dp = Dispatcher()
    await dp.emit_startup()
    try:
        yield dp
    finally:
        await dp.emit_shutdown()


@pytest.fixture(scope="session")
def event_loop():
    return asyncio.get_event_loop()