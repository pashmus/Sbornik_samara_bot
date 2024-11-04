import pytest
from aiogram import Dispatcher, Bot

from config_data.config import Config, load_config
import psycopg2
from email.message import Message
from unittest.mock import AsyncMock
from lexicon.lexicon import Lexicon
from main import welcome
from aiogram.enums import ParseMode

from tests.utils import get_update, get_message


# @pytest.mark.parametrize(
# "user_id, action",
#     [
#         (597856040, '/fvrt'),
#         (597856040, '200'),
#     ]
# )

@pytest.mark.asyncio
async def test_welcome(dispatcher: Dispatcher, bot: Bot):
    await dispatcher.feed_update(bot=bot, update=get_update(message=get_message(text='/start')))
    # msg = AsyncMock()
    # await welcome(msg)
    # msg.answer.assert_called_with(text=Lexicon().welcome_msg, parse_mode=ParseMode.HTML)
    message.answer.assert_called_with(text=Lexicon().welcome_msg, parse_mode=ParseMode.HTML)


# def test_example(example_fixture):
#     assert example_fixture == "Hello, World!"
