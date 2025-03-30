#!/bin/bash

# Переменные
BACKUP_DIR="/home/sbornik_bot_admin/Sbornik_samara_bot/db_backups"
DB_NAME="sbornik_bot_db"
DB_USER="avp"
DATE=$(date +%Y%m%d)
BACKUP_FILE="$BACKUP_DIR/bot_$DATE.backup"

# Создание резервной копии
echo "[$(date +"%Y-%m-%d %H:%M:%S")] Начало резервного копирования базы данных $DB_NAME в файл $BACKUP_FILE" >> $BACKUP_DIR/backup.log
pg_dump -U $DB_USER -h localhost -F c -b -v -f $BACKUP_FILE $DB_NAME

# Проверка успешности выполнения
if [ $? -eq 0 ]; then
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] Резервное копирование успешно завершено" >> $BACKUP_DIR/backup.log
else
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] Ошибка при резервном копировании" >> $BACKUP_DIR/backup.log
fi

# Удаление старых резервных копий (старше 30 дней)
find $BACKUP_DIR -type f -name "*.backup" -mtime +180 -exec rm -f {} \;
echo "[$(date +"%Y-%m-%d %H:%M:%S")] Удалены резервные копии старше 180 дней" >> $BACKUP_DIR/backup.log

# Этот файл переносим на сервер (через гит)
# Затем на сервере делаем этот скрипт исполняемым: chmod +x /home/sbornik_bot_admin/Sbornik_samara_bot/backup_script.sh
#
# Настройка cron ("Command Run On" или «Chronos»):
# Открой файл crontab для редактирования: crontab -e
# Добавь следующую строку: 0 5 * * 1 /home/sbornik_bot/backup_script.sh
# 0 5 * * 1 — означает "в 5:00 утра каждый понедельник".
# Сохрани и закрой файл.
# Чтобы убедиться, что cron работает, можешь временно изменить расписание на более частое (например, каждую минуту):
# * * * * * /home/sbornik_bot/backup_script.sh
# После проверки верни расписание на 0 5 * * 1.
#
# Очистка старых резервных копий (опционально):
# Если ты хочешь автоматически удалять старые резервные копии (например, старше 30 дней), добавь в скрипт следующие строки:
# # Удаление старых резервных копий (старше 30 дней)
# find $BACKUP_DIR -type f -name "*.backup" -mtime +30 -exec rm -f {} \;
# echo "[$(date +"%Y-%m-%d %H:%M:%S")] Удалены резервные копии старше 30 дней" >> $BACKUP_DIR/backup.log
#
# Сохраняем пароль через .pgpass (доступ только у пользователя):
# Создай файл .pgpass в домашней директории пользователя, от которого будет запускаться cron (обычно это /home/username/.pgpass):
# nano ~/.pgpass
# Добавь в файл строку в формате:
# localhost:5432:sbornik_bot_db:avp:your_password
# Установи права доступа к файлу, чтобы только владелец мог читать его:
# chmod 600 ~/.pgpass
# Теперь pg_dump будет автоматически использовать пароль из .pgpass, и тебе не нужно будет вводить его вручную.
#
#
#
#
#
#
#
#
#