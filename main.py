from dotenv import dotenv_values
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
from math import ceil

is_remote = False  # Переключение БД локальной или удалённой
config = dotenv_values(".env.remote") if is_remote else dotenv_values(".env")

token = config['TG_TOKEN']
host, user, password, database = config['HOST'], config['USER'], config['PASSWORD'], config['DATABASE']

bot = Bot(token=token)
dp = Dispatcher()

logging.basicConfig(filename='errors.log', level=logging.ERROR,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')  # Настройки логгирования
amount_songs = 376


@dp.message(CommandStart())  # Обработчик команды /start
async def welcome(message: Message):
    try:
        await message.answer(text='<b>Добро пожаловать!</b>\nОтправь боту номер песни или фразу из песни. Также найти '
                            'песню можно по названию на английском или по автору!\nА ещё, выбрав пункт <b>Меню</b>, '
                            'можно вывести список песен по некоторым авторам, по содержанию или "❤️ Избранное".',
                             parse_mode=ParseMode.HTML)
        metrics('users', message.from_user)
    except Exception as e:
        logging.exception(e)


@dp.message(((F.text.strip().lower() == 'admin') | (F.text.lower().startswith('select'))) &
            (F.from_user.id == int(config['my_tlgrm_id'])))
async def get_users_info(message: Message):
    try:
        conn = psycopg2.connect(host=host, user=user, password=password, dbname=database)
        cursor = conn.cursor()
        if message.text.strip().lower() == 'admin':
            cursor.execute(f"SELECT (SELECT COUNT( *) FROM users) AS a, (SELECT COUNT( *) FROM users "
                           f"WHERE last_access >= current_date) AS b, (SELECT COUNT(u.*) FROM users u JOIN periods p "
                           f"ON p.id = TO_CHAR(current_date, 'YYYY-MM') WHERE u.last_access "
                           f"BETWEEN p.dt_beg AND p.dt_end) AS c, (SELECT SUM(cnt_by_content + cnt_by_nums + "
                           f"cnt_by_txt + cnt_by_chords + cnt_by_audio_ru + cnt_by_media_en) FROM metrics) AS d")
            res = cursor.fetchone()
            await message.answer(f'users: {res[0]} \nusers today: {res[1]} \nusers month: {res[2]} \nqueries: {res[3]}')
        else:


            pass
            # cursor.execute("SELECT id, song_nums FROM themes ORDER BY id")
            # themes_songs = cursor.fetchall()
            # for theme in themes_songs:
            #     theme_id = theme[0]
            #     song_nums = [int(i) for i in theme[1].split(',')]
            #     for song_num in sorted(song_nums):
            #         cursor.execute(f"INSERT INTO theme_song_link (theme_id, song_num) VALUES ({theme_id}, {song_num})")
            # conn.commit()


            # cursor.execute(f"{message.text}")
            # my_select = cursor.fetchall()
            # output = '\n'.join(str(elem) for elem in my_select)
            # await message.answer(output)
        cursor.close()
        conn.close()
    except Exception as e:
        print(e)
        await message.answer(str(e))


@dp.message(F.text.in_({'/c1', '/c2', '/c3', '/c4', '/sgm', '/gt', '/tr', '/hill', '/kk', '/fvrt'}))
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
        elif c == '/fvrt':
            cursor.execute(f"SELECT s.num, s.name, s.alt_name, s.en_name FROM user_song_link usl "
                           f"JOIN songs s ON usl.song_num = s.num WHERE usl.tg_user_id  = {message.from_user.id}")
        res = cursor.fetchall()
        num_of_songs = len(res)
        cursor.close()
        conn.close()
        content = ['', '']
        for i in range(50 if num_of_songs > 50 else num_of_songs):
            content[0] += (f"\n{str(res[i][0])} - {res[i][1]}" + ("" if not res[i][2] else
                           f'\n        ({res[i][2]})') + ("" if not res[i][3] else f'\n        ({res[i][3]})'))
        for i in range(50, num_of_songs):
            content[1] += (f"\n{str(res[i][0])} - {res[i][1]}" + ("" if not res[i][2] else
                           f'\n        ({res[i][2]})') + ("" if not res[i][3] else f'\n        ({res[i][3]})'))
        if c in ('/gt', '/tr', '/hill', '/kk') or (c == '/fvrt' and num_of_songs < 25):
            btn_nums = {str(num[0]): str(num[0]) for num in res}
            width = (8 if ceil(num_of_songs/8) < ceil(num_of_songs/7)
                     else 7 if ceil(num_of_songs/7) < ceil(num_of_songs/6) else 6)
            kb = create_inline_kb(width, **btn_nums)  # Вызываем функцию строителя кнопок
            await message.answer(text=content[0], reply_markup=kb)
        else:
            for elem in content:
                if elem:
                    await message.answer(elem)
        metrics('cnt_by_content', message.from_user)
        metrics('users', message.from_user)
    except Exception as e:
        logging.exception(e)


# @dp.message(F.text == '/thm')
# async def get_themes(message: Message):
#     try:
#         conn = psycopg2.connect(host=host, user=user, password=password, dbname=database)
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM main_themes")
#         main_themes = cursor.fetchall()
#
#         btn_nums = {f"&;{m_theme_id};{m_theme}": f"🔸 {m_theme} 🔸" for m_theme_id, m_theme in main_themes}
#         kb = create_inline_kb(1, **btn_nums)  # Вызываем функцию строителя кнопок
#         await message.answer(text=f"📁 <b>Выберете категорию тем.</b>", parse_mode=ParseMode.HTML, reply_markup=kb)
#         cursor.close()
#         conn.close()
#     except Exception as e:
#         print(e)
#         logging.exception(e)
#

@dp.message(F.text == '/thm')
async def get_themes(message: Message):
    try:
        conn = psycopg2.connect(host=host, user=user, password=password, dbname=database)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM main_themes")
        main_themes = cursor.fetchall()
        cursor.execute("SELECT id, theme, main_theme_id FROM themes ORDER BY id ASC")
        themes = cursor.fetchall()
        for m_theme_id, m_theme in main_themes:
            btn_nums = {f'&;{theme[0]};{theme[1]}': theme[1] for theme in themes if theme[2] == m_theme_id}
            kb = create_inline_kb(1, **btn_nums)  # Вызываем функцию строителя кнопок
            gap: int = int(round((45 - len(m_theme)*2.5)))
            await message.answer(text=f"<b>🔸 {m_theme.upper()}{gap * ' '}.</b>",
                                 parse_mode=ParseMode.HTML, reply_markup=kb)
            # dashes: int = int(round((20 - len(m_theme)) / 1.9))
            # await message.answer(text=f"<b>{dashes * '- '}{m_theme.upper()}{dashes * ' -'}</b>", parse_mode=ParseMode.HTML, reply_markup=kb)
        cursor.close()
        conn.close()
    except Exception as e:
        print(e)
        logging.exception(e)


@dp.callback_query(F.data.startswith('&;'))
async def on_click_theme(callback: CallbackQuery):
    try:
        theme_id = int(callback.data.split(';')[1])
        conn = psycopg2.connect(host=host, user=user, password=password, dbname=database)
        cursor = conn.cursor()
        cursor.execute(f"SELECT s.num, s.name, s.alt_name, s.en_name FROM songs s JOIN theme_song_link tsl "
                       f"ON s.num = tsl.song_num WHERE tsl.theme_id = {theme_id}")
        res = cursor.fetchall()
        num_of_songs = len(res)
        content = ''
        btn_nums = {}
        if num_of_songs < 25:
            for song in res:
                content += (f"\n{str(song[0])} - {song[1]}" + ("" if not song[2] else
                            f"\n        ({song[2]})") + ("" if not song[3] else f"\n        ({song[3]})"))
                btn_nums[str(song[0])] = str(song[0])
            width = (8 if ceil(num_of_songs / 8) < ceil(num_of_songs / 7)
                     else 7 if ceil(num_of_songs / 7) < ceil(num_of_songs / 6) else 6)
            kb = create_inline_kb(width, **btn_nums)  # Вызываем функцию строителя кнопок
        else:
            for elem in res:
                content += (f"\n{str(elem[0])} - {elem[1]}" + ("" if not elem[2] else
                            f'\n        ({elem[2]})') + ("" if not elem[3] else f'\n        ({elem[3]})'))
            kb = None
        await bot.send_message(chat_id=callback.message.chat.id, text=f"🔹 <b>{callback.data.split(';')[2]}:</b>",
                               parse_mode=ParseMode.HTML)
        await bot.send_message(chat_id=callback.message.chat.id, text=content, reply_markup=kb)
        await callback.answer()
        cursor.close()
        conn.close()
    except Exception as e:
        print(e)
        logging.exception(e)


@dp.message(F.text.isdigit())  # Обработчик номеров песен
async def search_song_by_num(message: Message):
    try:
        num = message.text
        result = await return_song(num, message.from_user.id)  # Вызываем функцию поиска песни
        if result[0]:
            await message.answer(result[1], parse_mode=ParseMode.HTML, reply_markup=result[2])
        else:
            await message.answer(result[1])
        metrics('cnt_by_nums', message.from_user)
        metrics('users', message.from_user)
    except Exception as e:
        logging.exception(e)


@dp.callback_query(F.data.isdigit())  # Обработчик нажатия на кнопку с номером песни
async def on_click_song(callback: CallbackQuery):
    try:
        num = callback.data
        result = await return_song(num, callback.from_user.id)
        await bot.send_message(chat_id=callback.message.chat.id, text=result[1], parse_mode=ParseMode.HTML,
                               reply_markup=result[2])
        await callback.answer()
    except Exception as e:
        logging.exception(e)


async def return_song(num, tg_user_id):
    try:
        conn = psycopg2.connect(host=host, user=user, password=password, dbname=database)
        cursor = conn.cursor()
        cursor.execute(f"WITH upd_song AS (UPDATE songs SET cnt_using = COALESCE(cnt_using, 0) + 1 WHERE num = {num} "
                       f"RETURNING num, alt_name, text, en_name, authors, chords_file_id, audio_file_id, "
                       f"youtube_url) SELECT upd_song.*, EXISTS(SELECT 1 FROM user_song_link "
                       f"WHERE tg_user_id = {tg_user_id} AND song_num = {num}) FROM upd_song")
        res = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        sep = '____________________________'
        if res:
            kb = under_song_kb(2, res[8], res[6] is not None, res[7] is not None)  # Вызываем функцию клавы под песней
            return [True, (f'<i>{res[0]}</i>' + (f'  <b>{res[1]}</b>\n\n' if res[1] else '\n\n') +
                           f'{res[2]}\n{sep}' + (f'\n<b>{res[3]}</b>' if res[3] else '') +
                           (f'\n<i>{res[4]}</i>' if res[4] else '')), kb]
        else:
            return [False, (f'Песня не найдена. 🤷\nНужно отправить боту номер песни (1-{amount_songs}) или '
                            f'фразу из песни. Также найти песню можно по названию на английском или по автору!')]
    except Exception as e:
        logging.exception(e)


@dp.callback_query(F.data == 'favorites')  # Обработчик нажатия кнопки '🤍'
async def on_click_favorites(callback: CallbackQuery):
    try:
        kb: InlineKeyboardMarkup = callback.message.reply_markup  # Достаём объект клавиатуры
        song_in_fvrt: bool = kb.inline_keyboard[0][0].text == '❤️'  # Есть ли песня в избранном
        kb.inline_keyboard[0][0].text = '🤍' if song_in_fvrt else '❤️'  # Меняем цвет сердца на кнопке
        tg_user_id = callback.from_user.id
        num = callback.message.text.split()[0]
        conn = psycopg2.connect(host=host, user=user, password=password, dbname=database)
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM user_song_link WHERE tg_user_id={tg_user_id}")
        user_in_fvrt = cursor.fetchone()
        if song_in_fvrt:
            cursor.execute(f"DELETE FROM user_song_link WHERE tg_user_id = {tg_user_id} AND song_num = {num}")
        else:
            cursor.execute(f"INSERT INTO user_song_link VALUES ({tg_user_id}, {num})")
        conn.commit()
        cursor.close()
        conn.close()
        if song_in_fvrt:
            await callback.answer(text='Песня удалена из Избранного!')
        else:
            if user_in_fvrt:
                await callback.answer(text='Песня добавлена в Избранное!')
            else:
                await callback.answer(text='Песня добавлена в Избранное!\n'
                                           'Весь список с Избранным можно вывести через Меню.', show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception as e:
        logging.exception(e)


@dp.callback_query(F.data == 'Chords')  # Обработчик нажатия кнопки "Аккорды"
async def on_click_chords(callback: CallbackQuery):
    try:
        num = callback.message.text.split()[0]
        conn = psycopg2.connect(host=host, user=user, password=password, dbname=database)
        cursor = conn.cursor()
        cursor.execute(f"SELECT chords_file_id FROM songs where num = {num}")
        chords_file_id = cursor.fetchone()[0]
        if chords_file_id:
            await bot.send_photo(chat_id=callback.message.chat.id, photo=chords_file_id, caption=num)
        else:
            file = FSInputFile(f'Chords_jpg/{num}.jpg')
            photo_info = await bot.send_photo(chat_id=callback.message.chat.id, photo=file, caption=num)
            file_id = photo_info.photo[-1].file_id
            cursor.execute(f"UPDATE songs SET chords_file_id = '{file_id}' WHERE num = {num}")
            conn.commit()
        cursor.close()
        conn.close()
        metrics('cnt_by_chords', callback.from_user)
        await callback.answer()
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
        res = cursor.fetchall()
        num_of_songs = len(res) if len(res) < 25 else 24
        cursor.close()
        conn.close()
        song_list = '' if res else ('Песня не найдена. 🤷 \nОтправь боту номер песни или фразу из песни. '
                                    'Также найти песню можно по названию на английском или по автору!')
        for song in res[0:24]:
            song_list += (f"\n{str(song[0])} - {song[1]}" + ("" if not song[2] else f"\n        ({song[2]})") +
                          ("" if not song[3] else f"\n        ({song[3]})"))
        num_buttons = {str(num[0]): str(num[0]) for num in res[0:24]}
        width = (8 if ceil(num_of_songs / 8) < ceil(num_of_songs / 7)
                 else 7 if ceil(num_of_songs / 7) < ceil(num_of_songs / 6) else 6)
        kb = create_inline_kb(width, **num_buttons)  # Вызываем функцию строителя кнопок
        await message.answer(song_list + f'\n\n❗️ Показаны только первые 24 из {len(res)} найденных песен. '
                                f'Сформулируйте запрос точнее. 🤷‍♂️' if len(res) > 24 else song_list, reply_markup=kb)
        metrics('cnt_by_txt', message.from_user)
        metrics('users', message.from_user)
    except Exception as e:
        logging.exception(e)


# Функция строителя клавиатуры после песни
def under_song_kb(width: int, in_fvrt: bool, is_audio: bool, is_youtube: bool) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    fvrt_sign = '❤️' if in_fvrt else '🤍'
    fvrt_btn = InlineKeyboardButton(text=fvrt_sign, callback_data='favorites')
    chords_btn = InlineKeyboardButton(text='Аккорды', callback_data='Chords')
    audio_btn = InlineKeyboardButton(text='Аудио', callback_data='audio')
    youtube_btn = InlineKeyboardButton(text='YouTube', callback_data='YouTube')
    buttons: list[InlineKeyboardButton] = [fvrt_btn, chords_btn]
    if is_audio:
        buttons.append(audio_btn)
    if is_youtube:
        buttons.append(youtube_btn)
    kb_builder.row(*buttons, width=width)
    return kb_builder.as_markup()


# Функция строителя клавиатуры с номерами песен после списков
def create_inline_kb(width: int, *args: str, **kwargs: str) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    buttons: list[InlineKeyboardButton] = []
    if kwargs:
        for btn, txt in kwargs.items():
            buttons.append(InlineKeyboardButton(text=txt, callback_data=btn))
    kb_builder.row(*buttons, width=width)
    return kb_builder.as_markup()


def metrics(act, user_info):  # Аналитика
    try:
        user_id, f_name, l_name, username, lang = (user_info.id, user_info.first_name, user_info.last_name,
                                                   user_info.username, user_info.language_code)
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