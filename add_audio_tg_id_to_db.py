# Загрузка аудио в телеграм бот и запись audio_id в БД
# Перед выполнением поменять в Config is_db_remote

import os
import glob
import asyncio
from aiogram import Bot
from aiogram.types import FSInputFile
import asyncpg
from typing import List
# Импортируем конфигурацию
from config_data.config import Config, load_config

# Подставляем номер песни для обработки. Если нужно обработать несколько песен, в строке 50 выбираем папку
song_num = 337

# Загружаем конфигурацию
config: Config = load_config()

# Настройки из конфига
TELEGRAM_BOT_TOKEN = config.tg_bot.token
CHAT_ID = config.tg_bot.admin_id  # Используем admin_id как чат для загрузки
DB_CONFIG = {
    'host': config.db.db_host,
    'database': config.db.db_name,
    'user': config.db.db_user,
    'password': config.db.db_password
}

async def upload_audio_to_telegram(bot: Bot, file_path: str, caption: str = "") -> str:
    """Загружает аудиофайл в Telegram и возвращает file_id"""
    file_input = FSInputFile(file_path)
    try:
        message = await bot.send_audio(
            chat_id=CHAT_ID,
            audio=file_input,
            caption=caption
        )
        return message.audio.file_id
    except Exception as e:
        print(f"Ошибка при загрузке {file_path}: {e}")
        return ""


async def process_song_folders(bot: Bot) -> None:
    """Обрабатывает все папки с песнями и обновляет БД"""
    conn = await asyncpg.connect(**DB_CONFIG)

    # Получаем список всех папок с песнями
    # song_folders = glob.glob('Audio/*/')
    song_folders = glob.glob(f'Audio/{song_num}/')

    for folder in song_folders:
        try:
            num = int(os.path.basename(os.path.normpath(folder)))
            print(f"Обрабатываю песню №{num}")

            # Получаем все mp3-файлы в папке
            audio_files = glob.glob(f'{folder}*.mp3')

            if not audio_files:
                print(f"Нет аудиофайлов для песни №{num}")
                continue

            file_ids: List[str] = []
            for audio_file in audio_files:
                file_id = await upload_audio_to_telegram(bot, audio_file, f"Песня №{num}")
                if file_id:
                    file_ids.append(file_id)

            if file_ids:
                # Обновляем базу данных
                await conn.execute(
                    "UPDATE songs SET audio_file_id = $1 WHERE num = $2", ';'.join(file_ids), num
                )
                print(f"Обновлены file_id для песни №{num}")

        except Exception as e:
            print(f"Ошибка при обработке папки {folder}: {e}")

    await conn.close()


async def main():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        await process_song_folders(bot)
    finally:
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())