# Sbornik_samara_bot

## Настройка проекта
```shell
python -m venv venv
cp .env.example .env
```
В файле .env ввести свои данные


pip freeze > requirements.txt
source venv/bin/activate
pip install -r requirements.txt

Для удаления webhook открыть в браузере `https://api.telegram.org/bot{TOKEN}/deleteWebhook`