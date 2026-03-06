import os
import librosa
import numpy as np

def detect_bpm(audio_file_path):
    """
    Определяет темп (BPM) аудиофайла.
    """
    try:
        # Загрузка аудиофайла
        # duration=None загружает весь файл. Можно ограничить duration=30 для ускорения
        y, sr = librosa.load(audio_file_path, duration=60)

        # Определение темпа
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        
        # tempo может возвращаться как массив (в новых версиях librosa) или float
        if isinstance(tempo, np.ndarray):
            tempo = tempo.item()
            
        return round(tempo)
    except Exception as e:
        print(f"Ошибка при обработке {audio_file_path}: {e}")
        return None

def main():
    audio_dir = 'audio_test'
    output_file = 'bpm_results.txt'
    
    # Проверяем существование папки
    if not os.path.exists(audio_dir):
        print(f"Папка {audio_dir} не найдена.")
        return

    results = []

    print(f"Начинаю сканирование папки {audio_dir}...")
    
    files = os.listdir(audio_dir)
    audio_files = [f for f in files if f.lower().endswith(('.mp3', '.wav', '.flac', '.m4a'))]
    
    if not audio_files:
        print("Аудиофайлы не найдены.")
        return

    with open(output_file, 'w', encoding='utf-8') as f:
        for filename in audio_files:
            file_path = os.path.join(audio_dir, filename)
            print(f"Обработка: {filename}")
            
            bpm = detect_bpm(file_path)
            
            if bpm:
                result_line = f"{filename}: {bpm} BPM"
                print(f" -> {bpm} BPM")
                f.write(result_line + "\n")
                f.flush() # Записываем сразу
            else:
                print(" -> Не удалось определить BPM")

    print(f"\nГотово! Результаты сохранены в {output_file}")

if __name__ == "__main__":
    main()
