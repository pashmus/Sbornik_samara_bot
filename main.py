
from dotenv import dotenv_values
import re
from aiogram import Bot, Dispatcher, types, F
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
from aiogram.enums import ParseMode

is_remote = False  # Переключение БД локальной или удалённой
config = dotenv_values(".env.remote") if is_remote else dotenv_values(".env")

token = config['TG_TOKEN']
host, user, password, database = config['HOST'], config['USER'], config['PASSWORD'], config['DATABASE']

bot = Bot(token=token)  # AVP TEST
dp = Dispatcher()

logging.basicConfig(filename='errors.log', level=logging.ERROR,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')  # Настройки логгирования
amount_songs = 376

@dp.message(CommandStart())  # Обработчик команды /start
async def welcome(message: Message):
    try:
        await message.answer(text='Добро пожаловать! Отправь боту номер песни или фразу из песни. Также найти песню '
                                  'можно по названию на английском или по автору! А ещё, выбрав пункт МЕНЮ, ты сможешь '
                                  'сформировать список песен по некоторым авторам или по содержанию.')
        metrics('users', message)
    except Exception as e:
        logging.exception(e)


@dp.message((F.text.strip().lower() == 'admin') & (F.from_user.id == int(config['my_tlgrm_id'])))
async def get_users_info(message: Message):
    try:
        conn = psycopg2.connect(host=host, user=user, password=password, dbname=database)
        cursor = conn.cursor()
        cursor.execute(f"SELECT (SELECT COUNT( *) FROM users) AS a, (SELECT COUNT( *) FROM users "
                       f"WHERE last_access >= current_date) AS b, (SELECT COUNT(u.*) FROM users u JOIN periods p "
                       f"ON p.id = TO_CHAR(current_date, 'YYYY-MM') WHERE u.last_access "
                       f"BETWEEN p.dt_beg AND p.dt_end) AS c, (SELECT SUM(cnt_by_content + cnt_by_nums + "
                       f"cnt_by_txt + cnt_by_chords + cnt_by_audio_ru + cnt_by_media_en) FROM metrics) AS d")
        res = cursor.fetchone()
        cursor.close()
        conn.close()
        await message.answer(f'users: {res[0]} \nusers today: {res[1]} \nusers month: {res[2]} \nqueries: {res[3]}')
    except Exception as e:
        logging.exception(e)


@dp.message(F.text.in_({'/c1', '/c2', '/c3', '/c4', '/sgm', '/gt', '/tr', '/hill', '/kk'}))  # Обработчик содержания
async def get_contents(message: Message):  # Функция для получения разных списков песен
    try:
        c = message.text
        conn = psycopg2.connect(host=host, user=user, password=password, dbname=database)
        cursor = conn.cursor()
        if c == '/c1':
            cursor.execute("SELECT num, name, alt_name, en_name FROM songs WHERE num < 101 ORDER BY num")
        elif c == '/c2':
            cursor.execute("SELECT num, name, alt_name, en_name FROM songs WHERE num BETWEEN 101 and 200 ORDER BY num")
        elif c == '/c3':
            cursor.execute("SELECT num, name, alt_name, en_name FROM songs WHERE num BETWEEN 201 and 300 ORDER BY num")
        elif c == '/c4':
            cursor.execute("SELECT num, name, alt_name, en_name FROM songs WHERE num > 300 ORDER BY num")
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
        res = cursor.fetchall()
        cursor.close()
        conn.close()
        if c in ('/c1', '/c2', '/c3', '/c4', '/sgm'):  # Разбиваем список на два
            content = ['', '']
            for i in range(50):
                content[0] += (str(res[i][0]) + ' - ' + res[i][1] + ("" if not res[i][2] else
                    f'\n        ({res[i][2]})') + ("" if not res[i][3] else f'\n        ({res[i][3]})') + '\n')
            for i in range(50, len(res)):
                content[1] += (str(res[i][0]) + ' - ' + res[i][1] + ("" if not res[i][2] else
                    f'\n        ({res[i][2]})') + ("" if not res[i][3] else f'\n        ({res[i][3]})') + '\n')
            for elem in content:
                await message.answer(elem)
        else:
            content = ''
            for song in res:
                content += (str(song[0]) + ' - ' + song[1] + ("" if not song[2] else f'\n        ({song[2]})') +
                              ("" if not song[3] else f'\n        ({song[3]})') + '\n')
            await message.answer(content)
        metrics('cnt_by_content', message)
        metrics('users', message)
    except Exception as e:
        logging.exception(e)


@dp.message(F.text.isdigit())  # Обработчик номеров песен
async def search_song_by_num(message: Message):
    try:
        conn = psycopg2.connect(host=host, user=user, password=password, dbname=database)
        cursor = conn.cursor()
        cursor.execute(f"UPDATE songs SET cnt_using = COALESCE(cnt_using, 0) + 1 WHERE num = {message.text} "
                       f"RETURNING text, en_name, authors")
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        sep = '____________________________'
        if result:
            chords_butt = InlineKeyboardButton(text='Аккорды', callback_data='Chords')
            kb = InlineKeyboardMarkup(inline_keyboard=[[chords_butt]])
            await message.answer(result[0] + '\n' + sep + (f'\n<b>{result[1]}</b>' if result[1] else "") +
                        (f'\n<i>{result[2]}</i>' if result[2] else ""), parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await message.answer(f'Песня не найдена. 🤷\nНужно отправить боту номер песни (1-{amount_songs}) или '
                                 f'фразу из песни. Также найти песню можно по названию на английском или по автору!')
        metrics('cnt_by_nums', message)
        metrics('users', message)
    except Exception as e:
        logging.exception(e)

@dp.callback_query(F.data == 'Chords')  # Обработчик нажатия кнопки "Аккорды"
async def on_click_chords(callback: CallbackQuery):
    try:
        num = 5
        file = FSInputFile(f'Chords_jpg/{num}.jpg')
        await bot.send_photo(chat_id=callback.message.chat.id, photo=file)
        metrics('cnt_by_chords', callback.message)
    except Exception as e:
        logging.exception(e)


@dp.message(F.text)  # Обработчик поиска по фразе
async def search_song_by_text(message: Message):
    try:
        conn = psycopg2.connect(host=host, user=user, password=password, dbname=database)
        cursor = conn.cursor()
        cursor.execute(f"SELECT num, name, alt_name, en_name FROM songs WHERE REPLACE(name || ' ' || "
                       f"COALESCE(alt_name, '') || ' ' || text || ' ' || COALESCE(en_name, '') || ' ' || "
                       f"COALESCE(authors, ''), 'ё', 'е') @@ PHRASETO_TSQUERY(REPLACE('{message.text}', 'ё', 'е')) "
                       f"ORDER BY num")
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        song_list = '' if result else ('Песня не найдена. 🤷 \nОтправь боту номер песни или фразу из песни. '
                                       'Также найти песню можно по названию на английском или по автору!')
        for song in result[0:50]:
            song_list += (str(song[0]) + ' - ' + song[1] + ("" if not song[2] else f'\n        ({song[2]})') +
                          ("" if not song[3] else f'\n        ({song[3]})') + '\n')
        await message.answer(song_list + f'\n\n# Показаны только первые 50 из {len(result)} найденных песен. '
                                         f'Сформулируйте запрос точнее. #' if len(result) > 50 else song_list)
        metrics('cnt_by_txt', message)
        metrics('users', message)
    except Exception as e:
        logging.exception(e)


def metrics(act, message):  # Аналитика
    try:
        user_id, f_name, l_name, username, lang = (message.chat.id, message.from_user.first_name,
                            message.from_user.last_name, message.from_user.username, message.from_user.language_code)
        current_date = datetime.date.today()  # .isoformat()
        conn = psycopg2.connect(host=host, user=user, password=password, dbname=database)
        cursor = conn.cursor()
        if act == 'users':  # Запись пользователей в таблицу users
            cursor.execute(f"INSERT INTO users (telgrm_user_id, f_name, l_name, username, lang) VALUES ({user_id}, "
                           f"'{f_name}', '{l_name}', '{username}', '{lang}') ON CONFLICT (telgrm_user_id) DO UPDATE "
                        f"SET u_cnt_msg = users.u_cnt_msg + 1, last_access = current_timestamp(0) + INTERVAL '1 hours'")
        else:  # Запись показателей в таблицу metrics
            cursor.execute(f"SELECT p.id, m.id_period FROM periods p LEFT JOIN metrics m ON p.id = m.id_period "
                           f"WHERE current_date BETWEEN p.dt_beg and p.dt_end")
            id_period = cursor.fetchone()
            if not id_period[1]:  # Если текущего периода в metrics ещё нет, то...
                id_prev_period = str(datetime.date(current_date.year, current_date.month - 1, 1))[:7] \
                    if current_date.month > 1 else str(datetime.date(current_date.year - 1, 12, 1))[:7]
                cursor.execute(f"UPDATE metrics SET cnt_by_users = (SELECT COUNT(u.*) FROM users u JOIN periods p "
                               f"ON p.id = '{id_prev_period}' WHERE u.last_access BETWEEN p.dt_beg AND p.dt_end) "
                               f"WHERE id_period = '{id_prev_period}'")  # Запись кол-ва юзеров в прошлом месяце в metrics
                cursor.execute(f"INSERT INTO metrics (id_period) VALUES ('{id_period[0]}')")  # Запись новой строки в metrics
            if act == 'cnt_by_content':  # Счётчик использования содержания
                cursor.execute(f"UPDATE metrics SET cnt_by_content=cnt_by_content+1 WHERE id_period = '{id_period[0]}'")
            elif act == 'cnt_by_nums':  # Счётчик поиска по номерам
                cursor.execute(f"UPDATE metrics SET cnt_by_nums = cnt_by_nums + 1 WHERE id_period = '{id_period[0]}'")
            elif act == 'cnt_by_txt':  # Счётчик поиска по фразе
                cursor.execute(f"UPDATE metrics SET cnt_by_txt = cnt_by_txt + 1 WHERE id_period = '{id_period[0]}'")
            elif act == 'cnt_by_chords':  # Счётчик нажатия "Аккорды"
                cursor.execute(f"UPDATE metrics SET cnt_by_chords = cnt_by_chords + 1 WHERE id_period = '{id_period[0]}'")
                cursor.execute(f"UPDATE users SET u_cnt_chords = u_cnt_chords + 1, "
                            f"last_access = current_timestamp(0) + INTERVAL '1 hours' WHERE telgrm_user_id = {user_id}")
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