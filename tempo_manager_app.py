import streamlit as st
import os
import librosa
import numpy as np
import asyncio
import asyncpg
from typing import List, Dict, Optional
from config_data.config import Config, load_config
import sys
from streamlit.web import cli as stcli


'''
2 способа запускать:
- Через терминал: streamlit run tempo_manager_app.py
- по кнопке Play запускается эта же команда (прописано в if __name__ == "__main__").

Останавливать в терминале нажать Ctrl + C или нажать стоп.
'''

# Настройка страницы
st.set_page_config(page_title="Менеджер темпа песен", layout="wide")

@st.cache_resource
def get_config() -> Config:
    """Загружает конфигурацию один раз."""
    return load_config()

@st.cache_data
def detect_bpm(audio_file_path: str) -> Dict[str, any]:
    """
    Определяет темп (BPM) аудиофайла и возвращает список кандидатов.
    """
    try:
        # Загрузка аудиофайла
        y, sr = librosa.load(audio_file_path, duration=150)

        # Определение темпа (возвращает лучший)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

        if isinstance(tempo, np.ndarray):
            tempo = tempo.item()

        primary_bpm = round(tempo)

        # Генерируем кандидатов (производные темпы)
        candidates = [
            primary_bpm,
            round(primary_bpm * 2),
            round(primary_bpm / 2),
            round(primary_bpm * 1.5), # Для 3/4 и 6/8
            round(primary_bpm * (2/3))
        ]
        # Убираем дубликаты и нереалистичные значения (<30 или >250)
        candidates = sorted(list(set([c for c in candidates if 30 <= c <= 250])))

        # Если основной темп выпал из диапазона, вернем его все равно первым
        if primary_bpm not in candidates and primary_bpm > 0:
             candidates.insert(0, primary_bpm)

        return {
            "bpm": primary_bpm,
            "candidates": candidates
        }
    except Exception as e:
        st.error(f"Ошибка при обработке {audio_file_path}: {e}")
        return {"bpm": None, "candidates": []}

def get_audio_files(root_dir: str, start_num: int, end_num: int) -> Dict[str, List[str]]:
    """
    Сканирует папку и возвращает словарь: {номер_песни: [пути_к_файлам]}
    Фильтрует по диапазону номеров [start_num, end_num].
    """
    songs_data = {}

    if not os.path.exists(root_dir):
        st.error(f"Папка {root_dir} не найдена.")
        return songs_data

    # Получаем список папок (номеров песен)
    try:
        subdirs = [d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))]

        for subdir in subdirs:
            # Проверяем, что название папки - это число (номер песни)
            if not subdir.isdigit():
                continue

            song_num_int = int(subdir)
            if not (start_num <= song_num_int <= end_num):
                continue

            song_num = subdir
            dir_path = os.path.join(root_dir, subdir)

            audio_files = []
            for f in os.listdir(dir_path):
                if f.lower().endswith(('.mp3', '.wav', '.flac', '.m4a')):
                    audio_files.append(os.path.join(dir_path, f))

            if audio_files:
                songs_data[song_num] = audio_files

    except Exception as e:
        st.error(f"Ошибка при сканировании папок: {e}")

    return songs_data

async def update_tempo_in_db(song_num: int, tempo: int, time_signature: str, db_config: dict):
    """Обновляет темп и размер песни в БД."""
    conn = None
    try:
        conn = await asyncpg.connect(**db_config)

        if time_signature == "нет":
            # Если размер "нет", обновляем только темп
            await conn.execute(
                "UPDATE songs SET tempo = $1 WHERE num = $2",
                tempo, int(song_num)
            )
        else:
            # Обновляем темп и размер
            await conn.execute(
                "UPDATE songs SET tempo = $1, time_signature = $2 WHERE num = $3",
                tempo, time_signature, int(song_num)
            )
        return True
    except Exception as e:
        st.error(f"Ошибка БД (Песня {song_num}): {e}")
        return False
    finally:
        if conn:
            await conn.close()

import streamlit.components.v1 as components

# ... (предыдущий код)

def get_metronome_html(bpm, candidates):
    """Генерирует HTML код метронома с предустановленным BPM."""
    candidates_js = str(candidates)
    return f"""
<!DOCTYPE html>
<html>
<head>
<style>
    body {{ font-family: sans-serif; background-color: #f0f2f6; padding: 10px; border-radius: 5px; }}
    .controls {{ display: flex; flex-direction: column; gap: 10px; align-items: center; }}
    .bpm-display {{ font-size: 2em; font-weight: bold; color: #31333F; }}
    button {{
        padding: 8px 16px; border: none; border-radius: 4px;
        background-color: #FF4B4B; color: white; cursor: pointer; font-size: 1em;
        width: 100%;
    }}
    button:hover {{ background-color: #FF2B2B; }}
    button.secondary {{ background-color: #ffffff; color: #31333F; border: 1px solid #d6d6d6; }}
    button.secondary:hover {{ background-color: #f0f0f0; }}
    .slider-container {{ width: 100%; display: flex; align-items: center; gap: 10px; }}
    input[type=range] {{ flex-grow: 1; }}
</style>
</head>
<body>
    <div class="controls">
        <div class="bpm-display"><span id="bpm-val">{bpm}</span> BPM</div>

        <div class="slider-container">
            <button class="secondary" onclick="changeBpm(-1)" style="width:auto">-</button>
            <input type="range" id="bpm-slider" min="30" max="250" value="{bpm}" oninput="updateBpm(this.value)">
            <button class="secondary" onclick="changeBpm(1)" style="width:auto">+</button>
        </div>

        <button id="play-btn" onclick="togglePlay()">▶ Старт</button>
        <button class="secondary" onclick="nextCandidate()" id="candidate-btn" style="display:{'block' if candidates else 'none'}">Варианты ({", ".join(map(str, candidates))})</button>
    </div>

    <script>
        let audioContext = null;
        let isPlaying = false;
        let currentBpm = {bpm};
        let nextNoteTime = 0.0;
        let timerID = null;
        let lookahead = 25.0;
        let scheduleAheadTime = 0.1;
        let candidates = {candidates_js};
        let candidateIdx = 0;

        function initAudio() {{
            if (!audioContext) {{
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
            }}
            if (audioContext.state === 'suspended') {{
                audioContext.resume();
            }}
        }}

        function nextNote() {{
            const secondsPerBeat = 60.0 / currentBpm;
            nextNoteTime += secondsPerBeat;
        }}

        function scheduleNote(time) {{
            const osc = audioContext.createOscillator();
            const envelope = audioContext.createGain();

            osc.frequency.value = 1000;
            envelope.gain.value = 1;
            envelope.gain.exponentialRampToValueAtTime(1, time + 0.001);
            envelope.gain.exponentialRampToValueAtTime(0.001, time + 0.02);

            osc.connect(envelope);
            envelope.connect(audioContext.destination);

            osc.start(time);
            osc.stop(time + 0.03);
        }}

        function scheduler() {{
            while (nextNoteTime < audioContext.currentTime + scheduleAheadTime) {{
                scheduleNote(nextNoteTime);
                nextNote();
            }}
            timerID = window.setTimeout(scheduler, lookahead);
        }}

        function togglePlay() {{
            initAudio();
            isPlaying = !isPlaying;
            const btn = document.getElementById('play-btn');

            if (isPlaying) {{
                nextNoteTime = audioContext.currentTime + 0.05;
                scheduler();
                btn.innerText = "⏹ Стоп";
                btn.style.backgroundColor = "#333";
            }} else {{
                window.clearTimeout(timerID);
                btn.innerText = "▶ Старт";
                btn.style.backgroundColor = "#FF4B4B";
            }}
        }}

        function updateBpm(val) {{
            currentBpm = parseInt(val);
            document.getElementById('bpm-val').innerText = currentBpm;
            document.getElementById('bpm-slider').value = currentBpm;
        }}

        function changeBpm(delta) {{
            updateBpm(currentBpm + delta);
        }}

        function nextCandidate() {{
            if (candidates.length === 0) return;
            candidateIdx = (candidateIdx + 1) % candidates.length;
            updateBpm(candidates[candidateIdx]);
        }}
    </script>
</body>
</html>
"""

def main():
    # CSS для расширения сайдбара
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] {
                min-width: 600px;
                max-width: 800px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("🎵 Менеджер темпа песен")

    config = get_config()

    # Настройки БД для подключения
    db_config_dict = {
        'host': config.db.db_host,
        'database': config.db.db_name,
        'user': config.db.db_user,
        'password': config.db.db_password
    }

    st.sidebar.header("Настройки")
    audio_folder = st.sidebar.text_input("Папка с аудио", value="audio")

    # Фильтр по диапазону песен
    st.sidebar.subheader("Диапазон песен")
    col_from, col_to = st.sidebar.columns(2)
    with col_from:
        range_start = st.number_input("С (№)", min_value=1, value=1, step=1)
    with col_to:
        range_end = st.number_input("По (№)", min_value=1, value=500, step=1)

    if st.sidebar.button("Сканировать папку"):
        st.session_state['scan_triggered'] = True

    # Встраиваем метроном в сайдбар
    with st.sidebar:
        st.markdown("---")
        st.header("⏱ Метроном")

        # Получаем BPM для инициализации (берем из session_state или дефолт)
        current_bpm_init = 120
        current_candidates_init = []

        if 'current_bpm_data' in st.session_state:
            current_bpm_init = st.session_state['current_bpm_data']['bpm']
            current_candidates_init = st.session_state['current_bpm_data']['candidates']

        metro_html = get_metronome_html(current_bpm_init, current_candidates_init)
        components.html(metro_html, height=200)

    # JavaScript для отправки данных в метроном при обновлении страницы
    # Мы используем st.markdown с unsafe_allow_html для инъекции скрипта,
    # который отправит postMessage в iframe метронома.
    # Это немного "хак", но стандартного способа отправить событие в компонент нет.
    # if 'current_bpm_data' in st.session_state:
    #    bpm_data = st.session_state['current_bpm_data']
    #    js_code = f"""
    #        <script>
    #            // Находим iframe метронома (он будет внутри shadow-root или просто iframe)
    #            // Streamlit оборачивает компоненты. Попробуем отправить всем.
    #            setTimeout(function() {{
    #                const iframes = document.getElementsByTagName('iframe');
    #                for (let i = 0; i < iframes.length; i++) {{
    #                    iframes[i].contentWindow.postMessage({{
    #                        type: 'set_bpm',
    #                        bpm: {bpm_data['bpm']},
    #                        candidates: {bpm_data['candidates']}
    #                    }}, '*');
    #                }}
    #            }}, 1000); // Небольшая задержка, чтобы iframe успел загрузиться
    #        </script>
    #    """
    #    components.html(js_code, height=0, width=0)

    if 'scan_triggered' not in st.session_state:
        st.info("Нажмите 'Сканировать папку' в боковом меню для начала.")
        return

    songs_data = get_audio_files(audio_folder, range_start, range_end)

    if not songs_data:
        st.warning("Песни не найдены.")
        return

    st.success(f"Найдено песен: {len(songs_data)}")


    st.subheader("Результаты анализа")

    # Сортируем по номеру песни
    sorted_song_nums = sorted(songs_data.keys(), key=lambda x: int(x))

    updates_to_apply = [] # Список словарей с данными для обновления

    for song_num in sorted_song_nums:
        st.markdown(f"### Песня №{song_num}")
        files = songs_data[song_num]

        # Сначала получаем BPM для всех треков (кэшировано)
        track_bpms = []
        for f in files:
            track_bpms.append(detect_bpm(f))

        # Функция обратного вызова для обновления BPM при смене трека
        def update_input_bpm(s_num, bpms_data):
            radio_k = f"radio_{s_num}"
            input_k = f"input_{s_num}"
            if radio_k in st.session_state:
                idx = st.session_state[radio_k]
                data = bpms_data[idx]
                val = data['bpm'] if data['bpm'] else 0
                st.session_state[input_k] = val

                # Сохраняем данные для метронома
                st.session_state['current_bpm_data'] = {
                    'bpm': val,
                    'candidates': data['candidates']
                }

        # Функция обратного вызова для модификации BPM
        def modify_bpm(key_name, factor):
            if key_name in st.session_state:
                 st.session_state[key_name] = round(st.session_state[key_name] * factor)

        # Верхний блок: Выбор трека и Ввод BPM рядом
        top_col1, top_col2 = st.columns([3, 2])

        with top_col1:
            # Контейнер для выбора трека
            selected_track_idx = st.radio(
                f"Выберите трек для песни {song_num}:",
                options=range(len(files)),
                format_func=lambda x: os.path.basename(files[x]),
                key=f"radio_{song_num}",
                label_visibility="collapsed",
                on_change=update_input_bpm,
                args=(song_num, track_bpms)
            )

        # Берем BPM выбранного трека для инициализации
        selected_bpm_data = track_bpms[selected_track_idx]
        selected_bpm = selected_bpm_data['bpm']

        # Если это первый рендер или смена песни, обновляем метроном для текущего трека
        # (но осторожно, чтобы не перебивать ручной выбор пользователя)
        # Простейший способ - обновлять всегда при рендере активного блока
        # Но так как мы в цикле, это сложно.
        # Лучше полагаться на on_change и кнопку "Отправить в метроном" (опционально)

        # Кнопка для ручной отправки в метроном (если авто не сработало)
        if st.button("⏱ В метроном", key=f"to_metro_{song_num}"):
             st.session_state['current_bpm_data'] = {
                    'bpm': selected_bpm,
                    'candidates': selected_bpm_data['candidates']
                }
             st.rerun()

        with top_col2:
            # Компактный ряд: Input | Checkbox | Кнопки
            # Немного увеличим ширину кнопок (было 0.6) и уменьшим чекбокс (было 1.2)
            c_in, c_ch, c_b1, c_b2, c_b3, c_b4 = st.columns([1.5, 0.9, 0.7, 0.7, 0.7, 0.7])

            if f"input_{song_num}" not in st.session_state:
                st.session_state[f"input_{song_num}"] = selected_bpm if selected_bpm else 0

            with c_in:
                final_bpm = st.number_input(
                    "BPM", min_value=0, step=1, key=f"input_{song_num}", label_visibility="collapsed"
                )
            with c_ch:
                use_this = st.checkbox("Сохр.", value=(final_bpm > 0), key=f"check_{song_num}")

            # Используем on_click для изменения состояния до рендеринга виджета number_input в следующем прогоне
            # и use_container_width=True для одинаковой ширины
            c_b1.button("½", key=f"half_{song_num}", on_click=modify_bpm, args=(f"input_{song_num}", 0.5), use_container_width=True)
            c_b2.button("×2", key=f"double_{song_num}", on_click=modify_bpm, args=(f"input_{song_num}", 2), use_container_width=True)
            c_b3.button("×3", key=f"triple_{song_num}", on_click=modify_bpm, args=(f"input_{song_num}", 3), use_container_width=True)
            c_b4.button("⅔", key=f"two_thirds_{song_num}", on_click=modify_bpm, args=(f"input_{song_num}", 2/3), use_container_width=True)

        # Отображаем детали для каждого трека (плееры)
        for idx, f_path in enumerate(files):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.audio(f_path)
                st.caption(os.path.basename(f_path))

            with col2:
                bpm = track_bpms[idx]['bpm']
                st.metric("BPM", f"{bpm}" if bpm else "N/A")

        # Выбор музыкального размера для всей песни
        st.write("Музыкальный размер:")
        time_sigs = ["нет", "2/4", "4/4", "3/4", "6/8"]
        selected_sig = st.radio(
            "Размер",
            options=time_sigs,
            index=2,
            horizontal=True,
            key=f"sig_{song_num}",
            label_visibility="collapsed"
        )

        if use_this and final_bpm > 0:
            updates_to_apply.append({
                'song_num': song_num,
                'tempo': final_bpm,
                'time_signature': selected_sig
            })

        st.divider()

    # Кнопка сохранения (вне формы)
    if st.button("Сохранить выбранные в БД", type="primary"):
        if not updates_to_apply:
            st.warning("Ничего не выбрано для сохранения.")
        else:
            progress_bar = st.progress(0)
            success_count = 0

            async def process_updates():
                nonlocal success_count
                for i, update_data in enumerate(updates_to_apply):
                    result = await update_tempo_in_db(
                        update_data['song_num'],
                        update_data['tempo'],
                        update_data['time_signature'],
                        db_config_dict
                    )
                    if result:
                        success_count += 1
                    progress_bar.progress((i + 1) / len(updates_to_apply))

            # Запускаем асинхронный цикл
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(process_updates())
            loop.close()

            st.success(f"Успешно обновлено песен: {success_count} из {len(updates_to_apply)}")
            # Можно добавить st.rerun(), чтобы сбросить галочки, но лучше оставить как есть


if __name__ == "__main__":
    if st.runtime.exists():
        main()
    else:
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
