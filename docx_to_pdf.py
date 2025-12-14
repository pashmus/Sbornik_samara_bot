import os
import comtypes.client

def convert_docx_to_pdf(input_path, output_path):
    word = comtypes.client.CreateObject("Word.Application")
    word.Visible = False
    try:
        doc = word.Documents.Open(input_path)
        doc.SaveAs(output_path, FileFormat=17)  # 17 = PDF
        doc.Close()
    finally:
        word.Quit()

folder = r'D:\\Work\\2023_Sbornik_Samara_Bot\\Sbornik_samara_bot\\converter_files\\docx_to_pdf'  # ← замени на путь к папке
for filename in os.listdir(folder):
    if filename.lower().endswith((".doc", ".docx")):
        in_path = os.path.join(folder, filename)
        out_path = os.path.splitext(in_path)[0] + ".pdf"
        print(f"Converting {filename} → {os.path.basename(out_path)}")
        convert_docx_to_pdf(in_path, out_path)


'''    ⚠️ Важно:

        Запускать от имени пользователя (не через WSL).
        Word не должен быть открыт вручную во время работы скрипта.
        Первый запуск может быть медленным (инициализация COM).'''