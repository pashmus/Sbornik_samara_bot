
from dotenv import dotenv_values
from aiogram import Bot, Dispatcher, F
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, InputMediaAudio,
                           InputMediaDocument, InputMediaPhoto,
                           InputMediaVideo, Message, FSInputFile)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart
from aiogram.filters.command import Command
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods.send_photo import SendPhoto

import logging
import psycopg2
import datetime

is_remote = True  # Переключение БД локальной или удалённой
config = dotenv_values(".env.remote") if is_remote else dotenv_values(".env")

token = config['TG_TOKEN']
host, user, password, database = config['HOST'], config['USER'], config['PASSWORD'], config['DATABASE']

bot = Bot(token=token)  # AVP TEST
dp = Dispatcher()

logging.basicConfig(filename='errors.log', level=logging.ERROR,  # Настройки логгирования
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
amount_songs = 366

@dp.message(CommandStart())  # Обработчик команды /start
async def welcome(message: Message):
    try:
        await message.answer(text='Добро пожаловать! Отправь боту номер песни или фразу из песни. Также найти песню '
                                  'можно по названию на английском или по автору! А ещё, выбрав пункт МЕНЮ, ты сможешь '
                                  'сформировать список песен по некоторым авторам или по содержанию.')
        metrics('users', message)
    except Exception as e:
        logging.exception(e)


@dp.message()  # Обработчик текстовых сообщений
async def search_song(message: Message):
    search_text = message.text.strip().lower()
    if search_text in ('users', 'users today', 'users month', 'queries'):
        if message.chat.id == 597856040:
            info = get_info(search_text)
            await message.answer(info)
    elif search_text in ('/c1', '/c2', '/c3', '/sgm', '/gt', '/tr', '/hill', '/kk'):
        content = get_contents(search_text)
        if type(content) is list:
            for elem in content:
                await message.answer(elem)
        else:
            await message.answer(content)
        metrics('cnt_by_content', message)
    elif search_text.isdigit():  # Если введенное значение является числом
        result = search_song_by_num(search_text)  # Ищем песню по номеру
        if int(search_text) <= amount_songs:
            global num_song
            num_song = int(search_text)
            chords_butt = InlineKeyboardButton(text='Аккорды', callback_data='Chords')
            keyword = InlineKeyboardMarkup(inline_keyboard=[[chords_butt]])
            await message.answer(result, reply_markup=keyword)
        else:
            await message.answer(text=result, show_alert=True)
        metrics('cnt_by_nums', message)
    else:
        if len(search_text) < 4:
            await message.answer('Запрос должен содержать более 3 символов.')
        else:
            result = search_song_by_text(search_text)  # Ищем песню по тексту
            await message.answer(result)
        metrics('cnt_by_txt', message)
    metrics('users', message)


@dp.callback_query(F.data == 'Chords')  # Обработчик нажатия кнопки "Аккорды"
async def on_click_chords(callback: CallbackQuery):
    try:
        file = FSInputFile(f'Chords_jpg/{num_song}.jpg')
        await bot.send_photo(chat_id=callback.message.chat.id, photo=file)
        metrics('cnt_by_chords', callback.message)
    except Exception as e:
        logging.exception(e)


# @dp.message()  # Обработчик ошибок
# async def handle_all_messages(message):
#     while True:
#         try:
#             search_song(message)
#             break
#         except Exception as e:
#             logging.exception(e)


def get_contents(c):  # Функция для получения разных списков песен
    try:
        conn = psycopg2.connect(host=host, user=user, password=password, dbname=database)
        cursor = conn.cursor()
        if c == '/c1':
            cursor.execute("SELECT num, name FROM songs WHERE num < 150 ORDER BY num")
        elif c == '/c2':
            cursor.execute("SELECT num, name FROM songs WHERE num BETWEEN 151 and 290 ORDER BY num")
        elif c == '/c3':
            cursor.execute("SELECT num, name FROM songs WHERE num > 290 ORDER BY num")
        # elif c == '/ch':
        #     cursor.execute("SELECT num, name, alt_name, en_name FROM songs WHERE num = ANY(string_to_array(("
        #                    "SELECT song_nums FROM themes WHERE theme = 'Рождество Христа'), ', ')::int[]) ORDER BY num")
        elif c == '/sgm':
            cursor.execute("SELECT num, name, alt_name, en_name FROM songs "
                           "WHERE authors ILIKE '%Sovereign Grace Music%' ORDER BY num")
        elif c == '/gt':
            cursor.execute("SELECT num, name, alt_name, en_name FROM songs WHERE authors ILIKE '%Getty%' "
                           "OR authors LIKE '%Townend%' OR authors LIKE '%CityAlight%' ORDER BY num")
        elif c == '/tr':
            cursor.execute("SELECT num, name, alt_name, en_name FROM songs "
                           "WHERE authors ILIKE '%Tomlin%' OR authors LIKE '%Redman%' ORDER BY num")
        elif c == '/hill':
            cursor.execute("SELECT num, name, alt_name, en_name FROM songs "
                           "WHERE authors ILIKE '%Hillsong%' ORDER BY num")
        elif c == '/kk':
            cursor.execute("SELECT num, name, alt_name, en_name FROM songs "
                           "WHERE authors ILIKE '%Краеугольный Камень%' ORDER BY num")
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        song_list = ''
        if c in ('/c1', '/c2', '/c3'):
            for song in result:
                song_list += f'{song[0]} - {song[1]}\n'
        elif c == '/sgm':  # Разбиваем список SGM на два.
            song_list = ['', '']
            for i in range(52):
                song_list[0] += (str(result[i][0]) + ' - ' + result[i][1] + ("" if not result[i][2] else
                    f'\n        ({result[i][2]})') + ("" if not result[i][3] else f'\n        ({result[i][3]})') + '\n')
            for i in range(52, len(result)):
                song_list[1] += (str(result[i][0]) + ' - ' + result[i][1] + ("" if not result[i][2] else
                    f'\n        ({result[i][2]})') + ("" if not result[i][3] else f'\n        ({result[i][3]})') + '\n')
        else:
            for song in result:
                song_list += (str(song[0]) + ' - ' + song[1] + ("" if not song[2] else f'\n        ({song[2]})') +
                              ("" if not song[3] else f'\n        ({song[3]})') + '\n')
        return song_list
    except Exception as e:
        logging.exception(e)


def search_song_by_num(song_num):  # Функция поиска песни по номеру
    try:
        conn = psycopg2.connect(host=host, user=user, password=password, dbname=database)
        cursor = conn.cursor()
        cursor.execute(f'SELECT text, en_name, authors FROM songs WHERE num = {song_num}')
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        sep = '___________________________________'
        if result:
            return f'{result[0]}\n{sep}\n{result[1] if result[1] else ""}\n{result[2] if result[2] else ""}'
        else:
            return (f'Песня не найдена. 🤷\nНужно отправить боту номер песни (1-{amount_songs}) или фразу из песни. '
                    f'Также найти песню можно по названию на английском или по автору!')
    except Exception as e:
        logging.exception(e)


def search_song_by_text(search_text):  # Функция поиска песни по фразе
    try:
        conn = psycopg2.connect(host=host, user=user, password=password, dbname=database)
        cursor = conn.cursor()
        cursor.execute(f"SELECT num, name FROM songs WHERE REPLACE(text, ',', '') ILIKE '%{search_text.replace(',', '')}%' "
                       f"OR REPLACE(name, ',', '') ILIKE '%{search_text.replace(',', '')}%' "
                       f"OR REPLACE(alt_name, ',', '') ILIKE '%{search_text.replace(',', '')}%'"
                       f"OR REPLACE(en_name, ',', '') ILIKE '%{search_text.replace(',', '')}%' "
                       f"OR REPLACE(authors, ',', '') ILIKE '%{search_text.replace(',', '')}%'")
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return '\n'.join([f'{song[0]} - {song[1]}' for song in result]) if result \
            else ('Песня не найдена. 🤷 \nОтправь боту номер песни или фразу из песни. '
                  'Также найти песню можно по названию на английском или по автору!')
    except Exception as e:
        logging.exception(e)


def get_info(my_query):
    try:
        conn = psycopg2.connect(host=host, user=user, password=password, dbname=database)
        cursor = conn.cursor()
        current_date = datetime.date.today()
        if my_query == 'users':
            cursor.execute("SELECT MAX(id) FROM users")
        elif my_query == 'users today':
            cursor.execute(f"SELECT COUNT(*) FROM users WHERE last_access >= '{current_date}'")
        elif my_query == 'users month':
            cursor.execute(f"SELECT COUNT(u.*) FROM users u JOIN periods p ON p.id = '{str(current_date)[:7]}' "
                           f"WHERE u.last_access BETWEEN p.dt_beg AND p.dt_end")
        elif my_query == 'queries':
            cursor.execute("SELECT SUM(cnt_by_content + cnt_by_nums + cnt_by_txt + cnt_by_chords + cnt_by_audio_ru + "
                           "cnt_by_media_en) FROM metrics")
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return str(result[0][0])
    except Exception as e:
        logging.exception(e)


def metrics(act, message):  # Аналитика
    try:
        user_id = message.chat.id
        current_date = datetime.date.today()  # .isoformat()
        conn = psycopg2.connect(host=host, user=user, password=password, dbname=database)
        cursor = conn.cursor()
        if act == 'users':  # Запись пользователей в таблицу users
            cursor.execute(f"WITH updated AS (UPDATE users SET u_cnt_msg = users.u_cnt_msg + 1, "
                           f"last_access = CAST(NOW() AS TIMESTAMP(0)) + INTERVAL '1 hours' "
                           f"WHERE telgrm_user_id = {user_id} RETURNING *) "
                           f"INSERT INTO users (telgrm_user_id, f_name, l_name, username, lang, first_access, last_access, "
                           f"u_cnt_msg, u_cnt_chords) SELECT {user_id}, '{message.from_user.first_name}', "
                           f"'{message.from_user.last_name}', '{message.from_user.username}', "
                           f"'{message.from_user.language_code}', current_date, current_timestamp, 1, 0 "
                           f"WHERE NOT EXISTS (SELECT 1 FROM updated)")
            # cursor.execute(f"SELECT telgrm_user_id FROM users WHERE telgrm_user_id = {user_id}")
            # if cursor.fetchone():  # Если user_id в users есть, то обновляем запись
            #     cursor.execute(f"UPDATE users SET last_access = CAST(NOW() AS TIMESTAMP(0)) + INTERVAL '1 hours', "
            #                    f"u_cnt_msg = users.u_cnt_msg + 1 WHERE telgrm_user_id = {user_id}")
            # else:  # Если нет, то создаём запись
            #     cursor.execute(f"INSERT INTO users (telgrm_user_id, f_name, l_name, username, lang, first_access, "
            #                    f"last_access, u_cnt_msg, u_cnt_chords) VALUES ({user_id}, '{message.from_user.first_name}',"
            #                    f"'{message.from_user.last_name}', '{message.from_user.username}', "
            #                    f"'{message.from_user.language_code}', current_date, current_timestamp, 1, 0)")
        else:  # Запись показателей в таблицу metrics
            cursor.execute(f"SELECT p.id, m.id_period FROM periods p LEFT JOIN metrics m ON p.id = m.id_period "
                           f"WHERE '{current_date}' BETWEEN p.dt_beg and p.dt_end")
            id_period = cursor.fetchone()
            if not id_period[1]:  # Если текущего периода в metrics ещё нет, то...
                id_prev_period = str(datetime.date(current_date.year, current_date.month - 1, 1))[:7] \
                    if current_date.month > 1 else str(datetime.date(current_date.year - 1, 12, 1))[:7]
                cursor.execute(f"UPDATE metrics SET cnt_by_users = (SELECT COUNT(u.*) FROM users u JOIN periods p "
                               f"ON p.id = '{id_prev_period}' WHERE u.last_access BETWEEN p.dt_beg AND p.dt_end) "
                               f"WHERE id_period = '{id_prev_period}'")  # Запись кол-ва юзеров в прошлом месяце в metrics
                cursor.execute(f"INSERT INTO metrics (cnt_by_content, cnt_by_nums, cnt_by_txt, cnt_by_chords, "
                               f"cnt_by_audio_ru, cnt_by_media_en, cnt_by_users, id_period) "
                               f"VALUES (0, 0, 0, 0, 0, 0, 0, '{id_period[0]}')")  # Запись новой строки в metrics
            if act == 'cnt_by_content':  # Счётчик использования содержания
                cursor.execute(f"UPDATE metrics SET cnt_by_content=cnt_by_content+1 WHERE id_period = '{id_period[0]}'")
            elif act == 'cnt_by_nums':  # Счётчик поиска по номерам
                cursor.execute(f"UPDATE metrics SET cnt_by_nums = cnt_by_nums + 1 WHERE id_period = '{id_period[0]}'")
            elif act == 'cnt_by_txt':  # Счётчик поиска по фразе
                cursor.execute(f"UPDATE metrics SET cnt_by_txt = cnt_by_txt + 1 WHERE id_period = '{id_period[0]}'")
            elif act == 'cnt_by_chords':  # Счётчик нажатия "Аккорды"
                cursor.execute(f"UPDATE metrics SET cnt_by_chords = cnt_by_chords + 1 WHERE id_period = '{id_period[0]}'")
                cursor.execute(f"UPDATE users SET u_cnt_chords = u_cnt_chords + 1 WHERE telgrm_user_id = {user_id}")
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logging.exception(e)


if __name__ == '__main__':  # Запуск бота
    try:
        dp.run_polling(bot)
    except Exception as e:
        logging.exception(e)