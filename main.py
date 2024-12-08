from config_data.config import Config, load_config
from lexicon.lexicon import Lexicon
from aiogram import Bot, Dispatcher, F
from aiogram.types import (CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, FSInputFile)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart
from aiogram.filters.command import Command
import logging
#import psycopg2
import asyncpg
import datetime
from aiogram.enums import ParseMode
from math import ceil
from typing import Any, List, Tuple, Dict, Union
import glob
# import asyncio

log_format = '[{asctime}] #{levelname:8} {filename}: {lineno} in {funcName} - {name} - {message}'
logging.basicConfig(filename='errors.log', level=logging.ERROR, format=log_format, style='{')

# is_db_remote = False  # Переключение БД локальной или удалённой
# config: Config = load_config(".env.remote") if is_db_remote else load_config(".env")
config: Config = load_config()
lexicon = Lexicon()

token = config.tg_bot.token
admin_id = config.tg_bot.admin_id
admin_username = config.tg_bot.admin_username
donat_card = config.card.card
db_name, db_host, db_user, db_password = config.db.db_name, config.db.db_host, config.db.db_user, config.db.db_password

bot = Bot(token=token)
dp = Dispatcher()


# Обработчик команды /start
@dp.message(CommandStart())
async def welcome(message: Message):
    try:
        await message.answer(text=lexicon.welcome_msg, parse_mode=ParseMode.HTML)
    except Exception as e:
        bot_user = message.from_user
        await message.answer(text=lexicon.error_msg)
        await bot.send_message(chat_id=admin_id, text=f'Error: {str(e)}\ndef welcome\nuser: '
                               f'{bot_user.id, bot_user.username, bot_user.first_name, bot_user.last_name}')
        logging.exception(e)
    finally:
        await metrics(act='welcome', user_info=message.from_user, data='/start')


@dp.message(((F.text.strip().lower() == 'admin') | (F.text.lower().startswith('select'))) &
            (F.from_user.id == admin_id))
async def get_users_info(message: Message):
    conn = await open_db_connection()
    try:
        if message.text.strip().lower() == 'admin':
            query_1 = """SELECT
                    (SELECT COUNT(*) FROM users) AS a,
                    (SELECT COUNT(*) FROM users WHERE last_access >= current_date) AS b,
                    (SELECT COUNT(u.*) FROM users u JOIN periods p ON p.id = TO_CHAR(current_date, 'YYYY-MM')
                     WHERE u.last_access BETWEEN p.dt_beg AND p.dt_end) AS c,
                    (SELECT SUM(cnt_by_content + cnt_by_nums + cnt_by_txt + cnt_by_chords + cnt_by_audio +
                    cnt_by_youtube) FROM metrics) AS d;"""
            res_1 = await conn.fetchrow(query_1)
            glob_stat = (f'Today_Users: {res_1[1]} \nMonth_Users: {res_1[2]} \n'
                         f'All_Users: {res_1[0]} \nAll_Requests: {res_1[3]}')

            query_2 = """SELECT to_char(ua.create_ts::date, 'YYYY-MM-DD') AS dt, 
                    count(DISTINCT tg_user_id) AS users_cnt, 
                    count(*) AS req_cnt 
                    FROM user_actions ua 
                    GROUP BY ua.create_ts::date 
                    ORDER BY dt DESC 
                    LIMIT 10;"""
            res_2 = await conn.fetch(query_2)
            daily_stat = format_stat_for_admin(res_2)

            await message.answer(daily_stat + '\n' + '-'*50 + '\n' + glob_stat)
        else:
            # Если админ отправил запрос который начинается с "SELECT"
            my_select = await conn.fetch(message.text)
            output = '\n'.join(str(elem) for elem in my_select)
            await message.answer(output)
    except Exception as e:
        await message.answer(str(e))
    finally:
        await close_db_connection(conn)


def format_stat_for_admin(results):
    # Заголовок таблицы
    header = f"{'Date':<19}|{'Users':<8}|{'Requests':<8}"
    separator = "-" * 50
    lines = [header, separator]
    # Добавление строк с результатами
    for row in results:
        date = row['dt']
        users_cnt = row['users_cnt']
        req_cnt = row['req_cnt']
        lines.append(f"{date:<14}|{users_cnt:<11}|{req_cnt:<8}")
    return "\n".join(lines)


# Функция для получения разных списков песен
@dp.message(Command(commands=['fvrt', 'sgm', 'gt', 'tr', 'hill', 'kk']))
async def get_song_list(message: Message):
    conn = await open_db_connection()
    try:
        c: str = message.text
        if c.startswith('/fvrt'):
            query = """SELECT s.num, s.name, s.alt_name, s.en_name FROM user_song_link usl 
                       JOIN songs s ON usl.song_num = s.num WHERE usl.tg_user_id = $1 ORDER BY create_ts DESC"""
            res = await conn.fetch(query, message.from_user.id)
        else:
            query: Dict[str: str] = {
                '/sgm': """SELECT num, name, alt_name, en_name FROM songs WHERE authors ILIKE '%Sovereign Grace Music%' 
                           ORDER BY num""",
                '/gt': """SELECT num, name, alt_name, en_name FROM songs WHERE authors ILIKE '%Getty%' 
                          OR authors LIKE '%Townend%' OR authors LIKE '%CityAlight%' ORDER BY num""",
                '/tr': """SELECT num, name, alt_name, en_name FROM songs 
                          WHERE authors ILIKE '%Tomlin%' OR authors LIKE '%Redman%' ORDER BY num""",
                '/hill': "SELECT num, name, alt_name, en_name FROM songs WHERE authors ILIKE '%Hillsong%' ORDER BY num",
                '/kk': """SELECT num, name, alt_name, en_name FROM songs WHERE authors ILIKE '%Краеугольный Камень%' 
                          ORDER BY num"""
            }
            res = await conn.fetch(query[c])

        num_of_songs = len(res)
        # Если в Избранном пусто
        if num_of_songs == 0 and c.startswith('/fvrt'):
            await message.answer(text=lexicon.fvrt_empty_msg, parse_mode=ParseMode.HTML)
        # Формируем список песен
        else:
            content = ['', '']
            for i in range(min(50, num_of_songs)):
                content[0] += (f"\n{str(res[i][0])} - {res[i][1]}" + ("" if not res[i][2] else
                               f'\n        ({res[i][2]})') + ("" if not res[i][3] else f'\n        ({res[i][3]})'))
            for i in range(50, num_of_songs):
                content[1] += (f"\n{str(res[i][0])} - {res[i][1]}" + ("" if not res[i][2] else
                               f'\n        ({res[i][2]})') + ("" if not res[i][3] else f'\n        ({res[i][3]})'))

            if c in ('/gt', '/tr', '/hill', '/kk', '/fvrt'):
                btn_nums = {f"song_btn;{num[0]}": str(num[0]) for num in res}
                width = row_width(num_of_btns=num_of_songs, max_width=8)
                kb = create_inline_kb(width, edit_btn='edit_fvrt' if c == '/fvrt' else None, **btn_nums)  # Вызываем функцию строителя кнопок
                await message.answer(text=(f"🗂 <b>ИЗБРАННОЕ</b>\n" if c == '/fvrt' else '') + content[0],
                                     parse_mode=ParseMode.HTML, reply_markup=kb)
            else:
                for elem in content:
                    if elem:
                        await message.answer(elem)
    except Exception as e:
        bot_user, txt = message.from_user, message.text
        await message.answer(text=lexicon.error_msg)
        await bot.send_message(chat_id=admin_id, text=f'Error: {str(e)}\ndef get_song_list; text: {txt}\nuser: '
                               f'{bot_user.id, bot_user.username, bot_user.first_name, bot_user.last_name}')
        logging.exception(e)
    finally:
        await close_db_connection(conn)
        c = message.text
        await metrics(act='get_song_list' if c in ('/sgm', '/gt', '/tr', '/hill', '/kk') else 'get_song_list_fvrt',
                      user_info=message.from_user, data=c)


@dp.message(Command(commands=['cont', 'thm', 'about', 'help']))
async def get_cont_thm_about_help(message: Message):
    try:
        c = message.text
        if c.startswith('/cont'):
            kb = get_content_keyboard()
            await message.answer(text=f"🗂 <b>Выберете диапазон содержания</b>", parse_mode=ParseMode.HTML,
                                 reply_markup=kb)
        elif c.startswith('/thm'):
            # Вызываем функцию строителя кнопок Категорий
            kb = create_inline_kb(1, **get_themes_btns('main_themes'))
            await message.answer(text=f"🗂 <b>Выберите категорию</b>", parse_mode=ParseMode.HTML, reply_markup=kb)
        elif c.startswith('/about') | c.startswith('/help'):
            await message.answer(text=lexicon.about_bot, parse_mode=ParseMode.HTML)
    except Exception as e:
        bot_user, txt = message.from_user, message.text
        await message.answer(text=lexicon.error_msg)
        await bot.send_message(chat_id=admin_id, text=f'Error: {str(e)}\ndef get_cont_thm_about_help; text: {txt}\n'
                                f'user: {bot_user.id, bot_user.username, bot_user.first_name, bot_user.last_name}')
        logging.exception(e)
    finally:
        await metrics(act='get_cont_thm_about_help', user_info=message.from_user, data=message.text)


# Редактирование Избранного (удаление песен, полная очистка)
@dp.callback_query(F.data.startswith('edit_fvrt'))
async def on_click_edit_or_del_fvrt(callback: CallbackQuery):
    conn = await open_db_connection()
    try:
        tg_user_id = callback.from_user.id
        data = callback.data
        # Если нажали Удалить песню из Избранного
        if data.startswith('edit_fvrt_del_song'):
            num = int(callback.data.split(';')[1])
            await conn.execute("DELETE FROM user_song_link WHERE tg_user_id = $1 AND song_num = $2;", tg_user_id, num)
        # Если нажали Очистить Избранное
        if data == 'edit_fvrt_clear_fvrt':
            await conn.execute(f"DELETE FROM user_song_link WHERE tg_user_id = $1;", tg_user_id)

        res = await conn.fetch("""SELECT s.num, s.name, s.alt_name, s.en_name 
                                  FROM user_song_link usl JOIN songs s ON usl.song_num = s.num 
                                  WHERE usl.tg_user_id = $1 ORDER BY create_ts DESC""", tg_user_id)
        num_of_songs = len(res)
        content = ''
        for i in range(num_of_songs):
            content += (f"\n{str(res[i][0])} - {res[i][1]}" + ("" if not res[i][2] else
                        f'\n        ({res[i][2]})') + ("" if not res[i][3] else f'\n        ({res[i][3]})'))

        btn_nums = {f"edit_fvrt_del_song;{num[0]}": f"❌ {str(num[0])}" for num in res}
        width = row_width(num_of_btns=num_of_songs, max_width=5)
        # Вызываем функцию строителя кнопок
        kb = create_inline_kb(width, clear_fvrt='edit_fvrt_clear_fvrt', back_btn='back_to_fvrt', **btn_nums)
        msg_spoiled = is_msg_spoiled(callback.message.date.replace(tzinfo=None))
        if callback.data.startswith('edit_fvrt_del_song'):
            await callback.answer(text='Песня удалена из Избранного!')
        if num_of_songs == 0:
            await callback.message.edit_text(text=lexicon.clear_fvrt, parse_mode=ParseMode.HTML)
        else:
            await (callback.message.delete() if not msg_spoiled else
                   callback.message.edit_text(text=f'Избранное смотри ниже...'))
            await callback.message.answer(text=f"🗂 <b>ИЗБРАННОЕ (Режим редактирования)</b>\n" + content,
                                          parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception as e:
        bot_user, txt = callback.from_user, callback.data
        await callback.message.answer(text=lexicon.error_msg)
        await bot.send_message(chat_id=admin_id, text=f'Error: {str(e)}\ndef on_click_edit_or_del_fvrt; text: {txt}\nuser: '
                               f'{bot_user.id, bot_user.username, bot_user.first_name, bot_user.last_name}')
        logging.exception(e)
    finally:
        await close_db_connection(conn)
        await metrics(act='on_click_edit_or_del_fvrt', user_info=callback.from_user, data=callback.data)


# @dp.callback_query(F.data.startswith('del_fvrt'))  # Обработчик нажатия на кнопку УДАЛЕНИЕ песни из избранного
# async def on_click_del_song_from_fvrt(callback: CallbackQuery):
#     try:
#         # num = int(callback.data.split(';')[1])
#         #kb: InlineKeyboardMarkup = callback.message.reply_markup  # Достаём объект исходной клавиатуры
#         # tg_user_id = callback.from_user.id
#         conn = psycopg2.connect(dbname=db_name, host=db_host, user=db_user, password=db_password)
#         cursor = conn.cursor()
#         await conn.execute(f"DELETE FROM user_song_link WHERE tg_user_id = {tg_user_id} AND song_num = {num}")
#         conn.commit()
#         await conn.execute(f"SELECT s.num, s.name, s.alt_name, s.en_name FROM user_song_link usl "
#                        f"JOIN songs s ON usl.song_num = s.num WHERE usl.tg_user_id  = {tg_user_id}")
#         res = cursor.fetchall()
#         cursor.close()
#         conn.close()
#         num_of_songs = len(res)
#         content = ''
#         for i in range(num_of_songs):
#             content += (f"\n{str(res[i][0])} - {res[i][1]}" + ("" if not res[i][2] else
#                         f'\n        ({res[i][2]})') + ("" if not res[i][3] else f'\n        ({res[i][3]})'))
#         btn_nums = {f"del_fvrt;{num[0]}": f"❌ {str(num[0])}" for num in res}
#         width = row_width(num_of_btns=num_of_songs, max_width=5)
#         kb = create_inline_kb(width, back_btn='fvrt', **btn_nums)  # Вызываем функцию строителя кнопок
#         msg_spoiled = is_msg_spoiled(callback.message.date.replace(tzinfo=None))
#         await callback.answer(text='Песня удалена из Избранного!')
#         await (callback.message.delete() if not msg_spoiled else
#                callback.message.edit_text(text=f'Избранное смотри ниже...'))
#         await callback.message.answer(text=f"🗂 <b>ИЗБРАННОЕ (Режим редактирования)</b>\n" + content,
#                                       parse_mode=ParseMode.HTML, reply_markup=kb)
#     except Exception as e:
#         bot_user, txt = callback.from_user, callback.data
#         await callback.message.answer(text=lexicon.error_msg)
#         await bot.send_message(chat_id=admin_id, text=f'Error: {str(e)}\ndef on_click_del_song_from_fvrt; text: {txt}'
#                                f'\nuser: {bot_user.id, bot_user.username, bot_user.first_name, bot_user.last_name}')
#         logging.exception(e)


@dp.callback_query(F.data == 'back_to_fvrt')
async def on_click_back_to_fvrt(callback: CallbackQuery):
    conn = await open_db_connection()
    try:
        res = await conn.fetch("""SELECT s.num, s.name, s.alt_name, s.en_name FROM user_song_link usl 
                                  JOIN songs s ON usl.song_num = s.num WHERE usl.tg_user_id = $1 
                                  ORDER BY create_ts DESC""", callback.from_user.id)
        num_of_songs = len(res)
        content = ['', '']
        for i in range(min(50, num_of_songs)):
            content[0] += (f"\n{str(res[i][0])} - {res[i][1]}" + ("" if not res[i][2] else
                                                                  f'\n        ({res[i][2]})') + (
                               "" if not res[i][3] else f'\n        ({res[i][3]})'))
        for i in range(50, num_of_songs):
            content[1] += (f"\n{str(res[i][0])} - {res[i][1]}" + ("" if not res[i][2] else
                                                                  f'\n        ({res[i][2]})') + (
                               "" if not res[i][3] else f'\n        ({res[i][3]})'))
        btn_nums = {f"song_btn;{num[0]}": str(num[0]) for num in res}
        width = row_width(num_of_btns=num_of_songs, max_width=8)
        kb = create_inline_kb(width, edit_btn='edit_fvrt', **btn_nums)  # Вызываем функцию строителя кнопок
        await callback.message.edit_text(text=f"🗂 <b>ИЗБРАННОЕ</b>\n" + content[0],
                                         parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception as e:
        bot_user = callback.from_user
        await callback.message.answer(text=lexicon.error_msg)
        await bot.send_message(chat_id=admin_id, text=f'Error: {str(e)}\ndef on_click_back_to_fvrt\nuser: '
                               f'{bot_user.id, bot_user.username, bot_user.first_name, bot_user.last_name}')
        logging.exception(e)
    finally:
        await close_db_connection(conn)
        await metrics(act='on_click_back_to_fvrt', user_info=callback.from_user, data='back_to_fvrt')


@dp.callback_query(F.data.startswith('cont'))
async def on_click_content(callback: CallbackQuery):
    conn = await open_db_connection()
    try:
        c = callback.data
        ranges = {
            'cont1': [1, 50],
            'cont2': [51, 100],
            'cont3': [101, 150],
            'cont4': [151, 200],
            'cont5': [201, 250],
            'cont6': [251, 300],
            'cont7': [301, 350],
            'cont8': [351, 400]
        }
        query = "SELECT num, name, alt_name, en_name FROM songs WHERE num BETWEEN $1 and $2 ORDER BY num"
        res = await conn.fetch(query, *ranges[c])
        num_of_songs = len(res)
        content = ''
        for i in range(num_of_songs):
            content += (f"\n{str(res[i][0])} - {res[i][1]}" + ("" if not res[i][2] else
                        f'\n        ({res[i][2]})') + ("" if not res[i][3] else f'\n        ({res[i][3]})'))
        kb = get_content_keyboard()
        msg_spoiled = is_msg_spoiled(callback.message.date.replace(tzinfo=None))
        await (callback.message.delete() if not msg_spoiled else
               callback.message.edit_text(text='Смотри ниже...'))
        await callback.message.answer(text=content, parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception as e:
        bot_user, txt = callback.from_user, callback.data
        await callback.message.answer(text=lexicon.error_msg)
        await bot.send_message(chat_id=admin_id, text=f'Error: {str(e)}\ndef on_click_content; text: {txt}\nuser: '
                               f'{bot_user.id, bot_user.username, bot_user.first_name, bot_user.last_name}')
        logging.exception(e)
    finally:
        await close_db_connection(conn)
        await metrics(act='on_click_content', user_info=callback.from_user, data=callback.data)


# Обработчик нажатия на Категорию. data = f"&;{m_theme_id};{m_theme}"
@dp.callback_query(F.data.startswith('&;'))
async def on_click_main_theme(callback: CallbackQuery):
    try:
        # Вызываем функцию строителя кнопок с темами
        kb = create_inline_kb(width=1, back_btn='to_main_themes_btn', **get_themes_btns(callback.data))
        await callback.message.edit_text(text=f'🔸 Категория <b>"{callback.data.split(";")[2]}":</b>',
                                         parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception as e:
        bot_user, txt = callback.from_user, callback.data
        await callback.message.answer(text=lexicon.error_msg)
        await bot.send_message(chat_id=admin_id, text=f'Error: {str(e)}\ndef on_click_main_theme; text: {txt}\nuser: '
                               f'{bot_user.id, bot_user.username, bot_user.first_name, bot_user.last_name}')
        logging.exception(e)
    finally:
        await metrics(act='on_click_main_theme', user_info=callback.from_user, data=callback.data)


# Обработчик нажатия на тему или Назад
@dp.callback_query(F.data.startswith('to_main_themes_btn') | F.data.startswith('%;'))
async def on_click_theme_or_back(callback: CallbackQuery):
    conn = await open_db_connection()
    try:
        data = callback.data
        if data == 'to_main_themes_btn':
            kb = create_inline_kb(1, **get_themes_btns('main_themes'))  # Вызываем функцию строителя кнопок Категорий
            await callback.message.edit_text(text=f"🗂 <b>Выберите категорию</b>", parse_mode=ParseMode.HTML,
                                             reply_markup=kb)
        else:
            m_theme = callback.message.text.split('"')[1]
            m_theme_id, theme_id = data.split(';')[1], data.split(';')[2]
            res = await conn.fetch("""SELECT s.num, s.name, s.alt_name, s.en_name FROM songs s 
                                      JOIN theme_song_link tsl ON s.num = tsl.song_num WHERE tsl.theme_id = $1""",
                                    int(theme_id))

            num_of_songs = len(res)
            content = f"🔹 <b>{data.split(';')[3]}:</b>\n"
            btn_nums = {}
            if num_of_songs < 25:
                for song in res:
                    content += (f"\n{str(song[0])} - {song[1]}" + ("" if not song[2] else
                                f"\n        ({song[2]})") + ("" if not song[3] else f"\n        ({song[3]})"))
                    btn_nums[f"song_btn;{song[0]}"] = str(song[0])
                width = row_width(num_of_btns=num_of_songs, max_width=8)
                # Вызываем функцию строителя кнопок с номерами песен
                kb = create_inline_kb(width=width, back_btn=f"song_btn;to_themes;{m_theme_id};{m_theme}", **btn_nums)
            else:
                for elem in res:
                    content += (f"\n{str(elem[0])} - {elem[1]}" + ("" if not elem[2] else
                                f'\n        ({elem[2]})') + ("" if not elem[3] else f'\n        ({elem[3]})'))
                # Вызываем функцию строителя кнопок с номерами песен
                kb = create_inline_kb(width=1, back_btn=f"song_btn;to_themes;{m_theme_id};{m_theme}")
            await callback.message.edit_text(text=content, parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception as e:
        bot_user, txt = callback.from_user, callback.data
        await callback.message.answer(text=lexicon.error_msg)
        await bot.send_message(chat_id=admin_id, text=f'Error: {str(e)}\ndef on_click_theme_or_back; text: {txt}\nuser:'
                               f' {bot_user.id, bot_user.username, bot_user.first_name, bot_user.last_name}')
        logging.exception(e)
    finally:
        await close_db_connection(conn)
        data = callback.data
        await metrics(act='on_click_theme' if data != 'to_main_themes_btn' else 'on_click_back_from_themes',
                      user_info=callback.from_user, data=data)


# Обработчик нажатия на кнопку с номером песни
@dp.callback_query(F.data.startswith('song_btn'))
async def on_click_song_or_back(callback: CallbackQuery) -> None:
    try:
        key_data = callback.data.split(';')[1]
        if key_data == 'to_themes':
            # Вызываем функцию строителя кнопок с темами
            kb = create_inline_kb(1, back_btn='to_main_themes_btn', **get_themes_btns(f"&;{callback.data.split(';')[2]}"))
            await callback.message.edit_text(text=f'🔸 Категория <b>"{callback.data.split(";")[3]}":</b>',
                                             parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            # Вызываем функцию поиска песни
            result = await return_song(num=int(key_data), tg_user_id=callback.from_user.id)
            await callback.message.answer(text=result[1], parse_mode=ParseMode.HTML, reply_markup=result[2])
            await callback.answer()
    except Exception as e:
        bot_user, txt = callback.from_user, callback.data
        await callback.message.answer(text=lexicon.error_msg)
        await bot.send_message(chat_id=admin_id, text=f'Error: {str(e)}\ndef on_click_song_or_back; text: {txt}\nuser: '
                               f'{bot_user.id, bot_user.username, bot_user.first_name, bot_user.last_name}')
        logging.exception(e)
    finally:
        key_data = callback.data.split(';')[1]
        await metrics(act='on_click_song' if key_data != 'to_themes' else 'on_click_back_from_theme_songs',
                      user_info=callback.from_user, data=callback.data)


# Обработчик ввода номера песни
@dp.message(F.text.isdigit())
async def search_song_by_num(message: Message) -> None:
    try:
        num = int(message.text)
        # Вызываем функцию поиска песни
        result: List[Union[bool, str, InlineKeyboardMarkup]] = await return_song(num=num, tg_user_id=message.from_user.id)
        if result[0]:
            await message.answer(result[1], parse_mode=ParseMode.HTML, reply_markup=result[2])
        else:
            await message.answer(result[1])
    except Exception as e:
        bot_user, txt = message.from_user, message.text
        await message.answer(text=lexicon.error_msg)
        await bot.send_message(chat_id=admin_id, text=f'Error: {str(e)}\ndef search_song_by_num; text: {txt}\nuser: '
                               f'{bot_user.id, bot_user.username, bot_user.first_name, bot_user.last_name}')
        logging.exception(e)
    finally:
        await metrics(act='search_song_by_num', user_info=message.from_user, data=int(message.text))


async def return_song(num, tg_user_id) -> List[Union[bool, str, InlineKeyboardMarkup]]:
    conn = await open_db_connection()
    try:
        query = f"""WITH upd_song AS (
                UPDATE songs SET cnt_using = COALESCE(cnt_using, 0) + 1 WHERE num = $1 
                RETURNING num, name, alt_name, text, en_name, authors, chords_file_id, audio_file_id, youtube_url) 
                SELECT upd_song.*, EXISTS(SELECT 1 FROM user_song_link WHERE tg_user_id = $2 AND song_num = $1) 
                FROM upd_song;"""
        res = await conn.fetchrow(query, num, tg_user_id)
        sep = '____________________________'
        if res:
            # Вызываем функцию строителя клавиатуры под песней
            kb: InlineKeyboardMarkup = under_song_kb(width=2, in_fvrt=res[9], is_audio=res[7] is not None,
                                                     is_youtube=res[8] is not None)
            return [True, (f'<i>{res[0]}</i>' + (f'  <b>{res[2]}</b>\n\n' if res[2] else f'  <b>{res[1]}</b>\n\n') +
                           f'{res[3]}\n{sep}' + (f'\n<b>{res[4]}</b>' if res[4] else '') +
                           (f'\n<i>{res[5]}</i>' if res[5] else '')), kb]
        else:
            return [False, lexicon.not_found_by_num]
    except Exception as e:
        logging.exception(e)
    finally:
        await close_db_connection(conn)


# Обработчик нажатия кнопки '🤍'
@dp.callback_query(F.data == 'fvrt_btn')
async def on_click_favorites(callback: CallbackQuery):
    conn = await open_db_connection()
    try:
        # Достаём объект клавиатуры
        kb: InlineKeyboardMarkup = callback.message.reply_markup
        # Есть ли песня в избранном (только визуально)
        heart_is_red: bool = kb.inline_keyboard[0][0].text == '❤️'
        tg_user_id = callback.from_user.id
        num = int(callback.message.text.split()[0] if callback.message.text else callback.message.caption.split()[0])
        fvrt = await conn.fetch("SELECT * FROM user_song_link WHERE tg_user_id = $1;", tg_user_id)
        num_of_songs = len(fvrt)
        if num_of_songs > 59:
            await callback.answer()
            await callback.message.answer(text=lexicon.fvrt_is_full, parse_mode=ParseMode.HTML)
            return
        res = await conn.fetchrow("SELECT * FROM user_song_link WHERE tg_user_id = $1 and song_num = $2;", tg_user_id, num)
        song_in_fvrt = True if res else False
        # Меняем цвет сердца на кнопке
        kb.inline_keyboard[0][0].text = '🤍' if song_in_fvrt else '❤️'
        if song_in_fvrt:
            await conn.execute("DELETE FROM user_song_link WHERE tg_user_id = $1 AND song_num = $2;", tg_user_id, num)
            await callback.answer(text='Песня удалена из Избранного!')
        else:
            await conn.execute("INSERT INTO user_song_link VALUES ($1, $2);", tg_user_id, num)
            if num_of_songs > 0:
                await callback.answer(text='Песня добавлена в Избранное!')
            else:
                await callback.answer(text='Песня добавлена в Избранное!\n'
                                           'Весь список с Избранным можно вывести через Меню.', show_alert=True)
        if song_in_fvrt == heart_is_red:
            await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception as e:
        bot_user = callback.from_user
        await callback.message.answer(text=lexicon.error_msg)
        await bot.send_message(chat_id=admin_id, text=f'Error: {str(e)}\ndef on_click_favorites\nuser: '
                               f'{bot_user.id, bot_user.username, bot_user.first_name, bot_user.last_name}')
        logging.exception(e)
    finally:
        await close_db_connection(conn)
        await metrics(act='on_click_favorites', user_info=callback.from_user,
                      data=f'on_click_red_heart {num}' if song_in_fvrt else f'on_click_white_heart {num}')


# Обработчик нажатия кнопки "Аккорды"
@dp.callback_query(F.data == 'Chords_btn')
async def on_click_chords(callback: CallbackQuery):
    conn = await open_db_connection()
    try:
        # Достаём объект клавиатуры
        kb: InlineKeyboardMarkup = callback.message.reply_markup
        kb.inline_keyboard[0][1].text, kb.inline_keyboard[0][1].callback_data = 'Текст', 'txt_btn'
        first_str = callback.message.text.split('\n')[0]
        num = int(first_str.split()[0])
        res = await conn.fetchrow("SELECT chords_file_id FROM songs where num = $1;", num)
        chords_file_id = res[0]
        msg_spoiled = is_msg_spoiled(callback.message.date.replace(tzinfo=None))
        await (callback.message.delete() if not msg_spoiled else
               callback.message.edit_text(text=f'Аккорды на песню "{first_str}" ниже...'))
        if chords_file_id:
            await callback.message.answer_photo(photo=chords_file_id, caption=first_str, reply_markup=kb)
        else:
            file = FSInputFile(f'Chords_jpg/{num}.jpg')
            photo_info = await callback.message.answer_photo(photo=file, caption=first_str, reply_markup=kb)
            file_id = photo_info.photo[-1].file_id
            await conn.execute("UPDATE songs SET chords_file_id = $1 WHERE num = $2;", file_id, num)
        await callback.answer()
    except Exception as e:
        bot_user = callback.from_user
        if e.args[0] in ("Telegram server says - Bad Request: message to delete not found",
                         "'InaccessibleMessage' object has no attribute 'reply_markup'"):
            await bot.send_message(chat_id=admin_id, text=f'''Скорее всего - двойной тап./ 
                                   Error: {str(e)}\ndef on_click_chords/
                                   user: {bot_user.id, bot_user.username, bot_user.first_name, bot_user.last_name}''')
        else:
            await callback.message.answer(text=lexicon.error_msg)
            await bot.send_message(chat_id=admin_id, text=f'Error: {str(e)}\ndef on_click_chords\nuser: '
                                   f'{bot_user.id, bot_user.username, bot_user.first_name, bot_user.last_name}')
            logging.exception(e)
    finally:
        await close_db_connection(conn)
        await metrics(act='on_click_chords', user_info=callback.from_user, data=num)


# Обработчик нажатия кнопки "Текст"
@dp.callback_query(F.data == 'txt_btn')
async def on_click_text(callback: CallbackQuery):
    try:
        num = int(callback.message.caption.split()[0])
        result = await return_song(num=num, tg_user_id=callback.from_user.id)
        await callback.answer()
        await callback.message.answer(text=result[1], parse_mode=ParseMode.HTML, reply_markup=result[2])
    except Exception as e:
        bot_user = callback.from_user
        await callback.message.answer(text=lexicon.error_msg)
        await bot.send_message(chat_id=admin_id, text=f'Error: {str(e)}\ndef on_click_text\nuser: '
                               f'{bot_user.id, bot_user.username, bot_user.first_name, bot_user.last_name}')
        logging.exception(e)
    finally:
        await metrics(act='on_click_txt_btn', user_info=callback.from_user, data=num)


# Обработчик нажатия кнопки "Аудио"
@dp.callback_query(F.data == 'audio_btn')
async def on_click_audio(callback: CallbackQuery):
    conn = await open_db_connection()
    try:
        first_str = callback.message.text.split('\n')[0] if callback.message.text else callback.message.caption
        num = int(first_str.split()[0])
        res = await conn.fetchrow("SELECT audio_file_id FROM songs where num = $1;", num)
        audio_file_id = res[0]
        if audio_file_id != 'yes':
            for elem in audio_file_id.split(';'):
                await callback.message.answer_audio(audio=elem, caption=first_str)
        else:
            file_id = []
            for file in glob.glob(f'Audio/{num}/*.mp3'):
                file_input = FSInputFile(file)
                audio_info = await callback.message.answer_audio(audio=file_input, caption=first_str)
                file_id.append(audio_info.audio.file_id)
            file_id_join = ';'.join(file_id)
            await conn.execute("UPDATE songs SET audio_file_id = $1 WHERE num = $2;", file_id_join, num)
        await callback.answer()
    except Exception as e:
        bot_user = callback.from_user
        await callback.message.answer(text=lexicon.error_msg)
        await bot.send_message(chat_id=admin_id, text=f'Error: {str(e)}\ndef on_click_audio\nuser: '
                               f'{bot_user.id, bot_user.username, bot_user.first_name, bot_user.last_name}')
        logging.exception(e)
    finally:
        await close_db_connection(conn)
        await metrics(act='on_click_audio', user_info=callback.from_user, data=num)


# Обработчик нажатия кнопки "YouTube"
@dp.callback_query(F.data == 'YouTube_btn')
async def on_click_youtube(callback: CallbackQuery):
    conn = await open_db_connection()
    try:
        num = int(callback.message.text.split()[0] if callback.message.text else callback.message.caption.split()[0])
        res = await conn.fetchrow("SELECT youtube_url FROM songs WHERE num = $1;", num)
        youtube_url = res[0]
        for elem in youtube_url.split(','):
            await callback.message.answer(text=elem)
        await callback.answer()
    except Exception as e:
        bot_user = callback.from_user
        await callback.message.answer(text=lexicon.error_msg)
        await bot.send_message(chat_id=admin_id, text=f'Error: {str(e)}\ndef on_click_youtube\nuser: '
                               f'{bot_user.id, bot_user.username, bot_user.first_name, bot_user.last_name}')
        logging.exception(e)
    finally:
        await close_db_connection(conn)
        await metrics(act='on_click_youtube', user_info=callback.from_user, data=num)


# Обработчик поиска по фразе
@dp.message(F.text)
async def search_song_by_text(message: Message):
    conn = await open_db_connection()
    try:
        txt = message.text
        query = """SELECT num, name, alt_name, en_name FROM songs 
                WHERE to_tsvector('russian', name || ' ' || COALESCE(alt_name, '') || ' ' || text || ' ' || 
                COALESCE(en_name, '') || ' ' || COALESCE(authors, '')) 
                @@ PHRASETO_TSQUERY('russian', $1) ORDER BY num;"""
        res = await conn.fetch(query, txt)
        num_of_songs = len(res) if len(res) < 25 else 24
        song_list = '' if res else lexicon.not_found_by_txt
        for song in res[0:24]:
            song_list += (f"\n{str(song[0])} - {song[1]}" + ("" if not song[2] else f"\n        ({song[2]})") +
                          ("" if not song[3] else f"\n        ({song[3]})"))
        btn_nums = {f"song_btn;{num[0]}": str(num[0]) for num in res[0:24]}
        # Вызываем функцию подсчёта оптимальной ширины ряда
        width = row_width(num_of_btns=num_of_songs, max_width=8)
        kb: InlineKeyboardMarkup = create_inline_kb(width, **btn_nums)
        await message.answer(song_list + f'\n\n❗️ Показаны только первые 24 из {len(res)} найденных песен. '
                                f'Сформулируйте запрос точнее. 🤷‍♂️' if len(res) > 24 else song_list, reply_markup=kb)
    except Exception as e:
        bot_user, txt = message.from_user, message.text
        await message.answer(text=lexicon.error_msg)
        await bot.send_message(chat_id=admin_id, text=f'Error: {str(e)}\ndef search_song_by_text; text: {txt}\nuser: '
                               f'{bot_user.id, bot_user.username, bot_user.first_name, bot_user.last_name}')
        logging.exception(e)
    finally:
        await close_db_connection(conn)
        await metrics(act='search_song_by_text', user_info=message.from_user, data=txt)


async def open_db_connection():
    try:
        #conn = await asyncpg.connect(f'postgresql://{db_user}:{db_password}@{db_host}/{db_name}')
        conn = await asyncpg.connect(
            database=db_name,
            host=db_host,
            user=db_user,
            password=db_password
        )
        return conn
    except Exception as e:
        logging.exception(e)
        return None


async def close_db_connection(conn):
    if conn:
        try:
            await conn.close()
            # await conn.commit() # с комитом пишет ошибку 'Connection' object has no attribute 'commit'
        except Exception as e:
            logging.exception(e)


# Функция строителя клавиатуры после песни
def under_song_kb(width: int, in_fvrt: bool, is_audio: bool, is_youtube: bool) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    fvrt_sign = '❤️' if in_fvrt else '🤍'
    fvrt_btn = InlineKeyboardButton(text=fvrt_sign, callback_data='fvrt_btn')
    chords_btn = InlineKeyboardButton(text='Аккорды', callback_data='Chords_btn')
    audio_btn = InlineKeyboardButton(text='Аудио', callback_data='audio_btn')
    youtube_btn = InlineKeyboardButton(text='YouTube', callback_data='YouTube_btn')
    buttons: list[InlineKeyboardButton] = [fvrt_btn, chords_btn]
    if is_audio:
        buttons.append(audio_btn)
    if is_youtube:
        buttons.append(youtube_btn)
    kb_builder.row(*buttons, width=width)
    return kb_builder.as_markup()


# Функция строителя клавиатуры с номерами песен после списков
def create_inline_kb(width, *args, back_btn = None, edit_btn = None, clear_fvrt = None, **kwargs) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    buttons: list[InlineKeyboardButton] = []
    clear_btn = InlineKeyboardButton(text='🗑 Удалить ВСЁ', callback_data=clear_fvrt)
    bck_btn = InlineKeyboardButton(text='⬅️ Н а з а д', callback_data=back_btn)
    edt_btn = InlineKeyboardButton(text='✏️ Редактировать', callback_data=edit_btn)
    if kwargs:
        for btn, txt in kwargs.items():
            buttons.append(InlineKeyboardButton(text=txt, callback_data=btn))
    kb_builder.row(*buttons, width=width)
    if clear_fvrt:
        kb_builder.row(clear_btn, bck_btn)
    else:
        if back_btn:
            kb_builder.row(bck_btn)
        if edit_btn:
            kb_builder.row(edt_btn)
    return kb_builder.as_markup()


# Формируем кнопки с темами
def get_themes_btns(theme):
    # conn = await open_db_connection()
    # if theme == 'main_themes':
    #     await conn.execute("SELECT * FROM main_themes")
    #     main_themes = cursor.fetchall()
    #     themes_btns = {f"&;{m_theme_id};{m_theme}": f"🔸 {m_theme} 🔸" for m_theme_id, m_theme in main_themes}
    #
    # else:
    #     m_theme_id = int(theme.split(';')[1])
    #     await conn.execute(f"SELECT id, theme FROM themes WHERE main_theme_id = {m_theme_id} ORDER BY id ASC")
    #     themes = cursor.fetchall()
    #     themes_btns = {f"%;{m_theme_id};{id};{theme}": f"🔹 {theme} 🔹" for id, theme in themes}
    # await close_db_connection(conn)

    # Чтобы не доставать списки тем каждый раз, ниже сделаны словари. Надо обновлять при изменениях тем.
    if theme == 'main_themes':
        themes_btns = lexicon.themes_btns
    else:
        m_theme_id = int(theme.split(';')[1])
        theme_dict = lexicon.theme_dict
        themes_btns = theme_dict[m_theme_id]
    return themes_btns


def get_content_keyboard():
    cont_btns = {'cont1': '1 - 50', 'cont2': '51 - 100', 'cont3': '101 - 150', 'cont4': '151 - 200',
                 'cont5': '201 - 250', 'cont6': '251 - 300', 'cont7': '301 - 350',
                 'cont8': f'351 - {config.amount_songs.amount_songs}'}
    cont_kb = create_inline_kb(4, **cont_btns)
    return cont_kb


# Проверяем протухло ли сообщение
def is_msg_spoiled(msg_tmstmp):
    current_time = datetime.datetime.now().replace(microsecond=0)
    delta = (current_time - msg_tmstmp)
    expires_after = datetime.timedelta(hours=51)
    return delta > expires_after


# Функция расчёта оптимальной ширины ряда кнопок
def row_width(num_of_btns, max_width=8):
    l, m, s = max_width, max_width - 1, max_width - 2
    width = (l if ceil(num_of_btns / l) < ceil(num_of_btns / m)
             else m if ceil(num_of_btns / m) < ceil(num_of_btns / s) else s)
    return width


# Аналитика
async def metrics(act, user_info, data=None):
    conn = await open_db_connection()
    try:
        user_id, f_name, l_name, username, lang = (user_info.id, user_info.first_name, user_info.last_name,
                                                   user_info.username, user_info.language_code)

        # Записывает новых пользователей или обновляет (ков-во использ., дата посл.исп.) старых
        query = ("""INSERT INTO users (tg_user_id, f_name, l_name, username, lang) VALUES ($1, $2, $3, $4, $5) 
                 ON CONFLICT (tg_user_id) DO UPDATE SET u_cnt_msg = users.u_cnt_msg + 1, last_access = now();""")
        await conn.execute(query, user_id, f_name, l_name, username, lang)
        # Записываем все действия пользователей
        await conn.execute("INSERT INTO user_actions (tg_user_id, action, data) VALUES ($1, $2, $3);", user_id, act, str(data))

        current_date = datetime.date.today()  # .isoformat()
        # Определяем текущий период
        id_period = await conn.fetchrow("""SELECT p.id, m.id_period FROM periods p LEFT JOIN metrics m
                                        ON p.id = m.id_period WHERE current_date BETWEEN p.dt_beg and p.dt_end;""")
        # Если текущего периода в metrics ещё нет, то записываем результат прошедшего месяца и создаём строку с новым в metrix
        if not id_period[1]:
            id_prev_period = (str(datetime.date(current_date.year, current_date.month - 1, 1))[:7] if
                              current_date.month > 1 else str(datetime.date(current_date.year - 1, 12, 1))[:7])
            # Запись кол-ва юзеров в прошлом месяце в metrics
            await conn.execute("""UPDATE metrics SET cnt_by_users = (
                                    SELECT COUNT(u.*) FROM users u JOIN periods p ON p.id = $1
                                    WHERE u.last_access BETWEEN p.dt_beg AND p.dt_end) WHERE id_period = $1;""",
                               id_prev_period)
            # Запись новой строки в metrics
            await conn.execute("INSERT INTO metrics (id_period) VALUES ($1);", id_period[0])

        # Словарь для заполнения счётчиков. ключ = def metrix(act), значение = поле в таблице metrix.
        act_dict = {
            'on_click_content': 'cnt_by_content', 'search_song_by_text': 'cnt_by_txt',
            'on_click_chords': 'cnt_by_chords', 'on_click_audio': 'cnt_by_audio', 'on_click_youtube': 'cnt_by_youtube',
            'get_song_list': 'cnt_by_singers', 'search_song_by_num': 'cnt_by_nums', 'on_click_song': 'cnt_by_nums',
            'on_click_edit_or_del_fvrt': 'cnt_by_fvrt', 'on_click_favorites': 'cnt_by_fvrt',
            'get_song_list_fvrt': 'cnt_by_fvrt', 'on_click_back_to_fvrt': 'cnt_by_fvrt',
            'on_click_main_theme': 'cnt_by_themes', 'on_click_theme': 'cnt_by_themes',
            'on_click_back_from_theme_songs': 'cnt_by_themes'
        }
        # Заполнение счётчиков
        if act in act_dict:
            await conn.execute(f"""UPDATE metrics SET {act_dict[act]} = {act_dict[act]} + 1 
                               WHERE id_period = TO_CHAR(NOW(), 'YYYY-MM');""")
        # Счётчик нажатия "Аккорды" в users
        if act == 'on_click_chords':
            await conn.execute("""UPDATE users SET u_cnt_chords = u_cnt_chords + 1, last_access = 
                                now() WHERE tg_user_id = $1;""", user_id)
    except Exception as e:
        logging.exception(e)
    finally:
        await close_db_connection(conn)


# Триггеры, функции, используемые в БД
#
# Функция при первом юзере за день, записывает кол-во юзеров вчера
# CREATE OR REPLACE FUNCTION insert_daily_users()
# RETURNS trigger as $$
# BEGIN
# 	IF NOT EXISTS (SELECT 1 FROM daily_users_count WHERE create_ts::date = (now() + interval '1 hour')::date)
# 	then
# 	insert into daily_users_count (num_of_users) values ((
# 	select count(distinct tg_user_id) from user_actions
# 	where create_ts >= (now() + interval '1 hour')::date - interval '1 day' and create_ts < (now() + interval '1 hour')::date));
# 	END IF;
# 	RETURN NEW;
# end;
# $$ language plpgsql;
#
# DROP TRIGGER IF exists daily_users_update_trigger on user_actions;
#
# create trigger daily_users_update_trigger
# after insert on user_actions
# for each row
# execute function insert_daily_users();


if __name__ == '__main__':  # Запуск бота
    try:
        dp.run_polling(bot)
    except Exception as e:
        logging.exception(e)


# async def main():
#     await bot.delete_webhook(drop_pending_updates=True)
#     await dp.start_polling(bot)
#
# asyncio.run(main())
