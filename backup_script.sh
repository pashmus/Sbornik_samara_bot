#!/bin/bash

# Переменные
BACKUP_DIR="/home/sbornik_bot/db_backups"
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