#!/bin/bash
# Скрипт для создания резервной копии базы данных Neon.tech (только последний бэкап)

# Загружаем переменные окружения, если скрипт запускается не из окружения с ними
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Проверяем, что DATABASE_URL установлена
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL is not set"
    exit 1
fi

# Создаём директорию для бэкапов, если её нет
BACKUP_DIR="backups"
mkdir -p "$BACKUP_DIR"

# Файл для последнего бэкапа (всегда с одним именем)
LATEST_BACKUP="$BACKUP_DIR/latest.sql"

# Выполняем дамп базы данных
echo "Creating database backup: $LATEST_BACKUP"
pg_dump "$DATABASE_URL" > "$LATEST_BACKUP"

if [ $? -eq 0 ]; then
    echo "Backup completed successfully."
else
    echo "Backup failed!"
    exit 1
fi
