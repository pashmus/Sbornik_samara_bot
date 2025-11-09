# Преобразование YouTube ссылок из БД в аудио
# Перед выполнением поменять в Config is_db_remote

import yt_dlp
import psycopg2
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError
import os
import re
from config_data.config import Config, load_config

# Загружаем конфигурацию
config: Config = load_config()

# Подставляем наши номера песен для преобразования
song_nums = '401'
# Подставляем путь для сохранения песен
path_for_audio_files = 'D:\\Work\\2023_Sbornik_Samara_Bot\\Sbornik_samara_bot\\Audio'

DB_CONFIG = {
    'host': config.db.db_host,
    'database': config.db.db_name,
    'user': config.db.db_user,
    'password': config.db.db_password
}


def sanitize_filename(filename):
    """Заменяет проблемные символы в названиях файлов"""
    # Список запрещенных символов в именах файлов
    forbidden_chars = r'[\\/*?:"<>|]'
    # Заменяем их на подчеркивание
    return re.sub(forbidden_chars, '_', filename)


def download_audio(youtube_url, output_path):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',  # Формат на выходе
            'preferredquality': '192',  # Качество (192 кбит/с)
        }],
        'ffmpeg_location': 'C:\\Users\\pashm\\Downloads\\Soft\\ffmpeg-2025-05-01-git-707c04fe06-full_build\\bin',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])


def add_metadata(filename, title, artist):
    try:
        # Создаем или загружаем существующие теги
        try:
            audio = EasyID3(filename)
        except ID3NoHeaderError:
            audio = EasyID3()

        audio['title'] = title
        audio['artist'] = artist
        audio.save(filename)
        print(f"Метаданные добавлены: {filename}")
    except Exception as e:
        print(f"Ошибка добавления метаданных ({filename}): {e}")


def process_youtube_links():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        # cur.execute("SELECT num, youtube_url FROM songs where num!= 361 and num > 300 order by num")
        cur.execute(f"SELECT num, youtube_url FROM songs where num in ({song_nums}) order by num")
        rows = cur.fetchall()

        for row in rows:
            num, link = row
            if not link:
                print(f"Пропуск: пустая ссылка (num: {num})")
                continue

            output_dir = os.path.join(path_for_audio_files, str(num))
            os.makedirs(output_dir, exist_ok=True)

            for single_link in link.split(','):
                single_link = single_link.strip()
                if not single_link:
                    continue

                try:
                    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                        info = ydl.extract_info(single_link, download=False)
                        raw_title = info.get('title', 'Unknown Title')
                        title = sanitize_filename(raw_title)  # Очищаем название от запрещенных символов
                        artist = info.get('uploader', 'Unknown Artist')

                    download_audio(single_link, output_dir)

                    # Формируем имя файла с очищенным названием
                    filename = os.path.join(output_dir, f"{title}.mp3")

                    if os.path.exists(filename):
                        add_metadata(filename, title, artist)
                    else:
                        # Проверяем альтернативные варианты имен файлов
                        alt_filename = os.path.join(output_dir, f"{sanitize_filename(raw_title.replace('|', '_'))}.mp3")
                        if os.path.exists(alt_filename):
                            add_metadata(alt_filename, title, artist)
                        else:
                            print(f"Файл не найден: {filename}. Проверьте: {alt_filename}")

                except Exception as e:
                    print(f"Ошибка обработки {single_link}: {e}")

    except Exception as e:
        print(f"Ошибка БД: {e}")
    finally:
        if cur: cur.close()
        if conn: conn.close()


if __name__ == "__main__":
    process_youtube_links()




# Альтернативный вариант на asyncpg. Но тут ещё не исключаются запрещённые символы для названия файла.
'''
import yt_dlp
import asyncpg
import os
import asyncio
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError
from config_data.config import Config, load_config

# Загружаем конфигурацию
config: Config = load_config()

# Номера песен для обработки
song_nums = '392'  # Можно указать несколько через запятую: '392,393,394'
# Подставляем путь для сохранения песен
path_for_audio_files = 'D:\\Work\\2023_Sbornik_Samara_Bot\\Sbornik_samara_bot__test\\Audio'

# Настройки базы данных
DB_CONFIG = {
    'host': config.db.db_host,
    'database': config.db.db_name,
    'user': config.db.db_user,
    'password': config.db.db_password
}


def sync_download_audio(youtube_url: str, output_path: str) -> None:
    """Синхронная функция для скачивания аудио"""
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'ffmpeg_location': 'C:\\Users\\pashm\\Downloads\\Soft\\ffmpeg-2025-05-01-git-707c04fe06-full_build\\bin',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])


def sync_add_metadata(filename: str, title: str, artist: str) -> None:
    """Синхронная функция для добавления метаданных"""
    try:
        try:
            audio = EasyID3(filename)
        except ID3NoHeaderError:
            audio = EasyID3()

        audio['title'] = title
        audio['artist'] = artist
        audio.save(filename)
        print(f"Метаданные добавлены: {filename}")
    except Exception as e:
        print(f"Ошибка добавления метаданных ({filename}): {e}")


def sync_get_video_info(url: str) -> tuple:
    """Синхронная функция для получения информации о видео"""
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get('title', 'Unknown Title').replace('/', '_')
        artist = info.get('uploader', 'Unknown Artist')
        return title, artist


async def process_single_song(num: int, youtube_url: str) -> None:
    """Асинхронная обработка одной песни"""
    if not youtube_url:
        print(f"Пропуск: пустая ссылка (num: {num})")
        return

    output_dir = os.path.join(path_for_audio_files, str(num))
    os.makedirs(output_dir, exist_ok=True)

    for single_url in youtube_url.split(','):
        single_url = single_url.strip()
        if not single_url:
            continue

        try:
            # Получаем информацию о видео (синхронный вызов)
            title, artist = sync_get_video_info(single_url)

            # Скачиваем аудио (синхронный вызов)
            sync_download_audio(single_url, output_dir)

            # Добавляем метаданные
            filename = os.path.join(output_dir, f"{title}.mp3")
            if os.path.exists(filename):
                sync_add_metadata(filename, title, artist)
                print(f"Успешно обработана песня №{num}: {title}")
            else:
                print(f"Файл не найден: {filename}")

        except Exception as e:
            print(f"Ошибка обработки {single_url}: {e}")


async def main():
    """Основная асинхронная функция"""
    conn = None
    try:
        # Подключаемся к базе данных
        conn = await asyncpg.connect(**DB_CONFIG)

        # Получаем список песен для обработки
        query = f"SELECT num, youtube_url FROM songs WHERE num IN ({song_nums}) ORDER BY num"
        records = await conn.fetch(query)

        # Обрабатываем каждую песню последовательно
        for record in records:
            num, youtube_url = record
            print(f"\nНачинаю обработку песни №{num}...")
            await process_single_song(num, youtube_url)

    except Exception as e:
        print(f"Критическая ошибка: {e}")
    finally:
        if conn:
            await conn.close()
        print("Обработка завершена")


if __name__ == "__main__":
    # Создаем новую event loop для asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Запускаем основную функцию
        loop.run_until_complete(main())
    finally:
        # Закрываем loop
        loop.close()
'''