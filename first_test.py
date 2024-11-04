import asyncio
from aiogram import Bot


API_TOKEN = '6646811837:AAGxIpZ5BOtI7EA0DSUyYF9xo7t-MGnE7U0'

async def send_message(chat_id, text):
    bot = Bot(token=API_TOKEN)
    await bot.send_message(chat_id, text)

async def load_test(chat_id, num_messages):
    tasks = []
    for _ in range(num_messages):
        tasks.append(send_message(chat_id, "/fvrt"))
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    chat_id = '597856040'
    num_messages = 2  # Количество сообщений для отправки
    asyncio.run(load_test(chat_id, num_messages))