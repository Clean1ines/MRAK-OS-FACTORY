#!/bin/bash
# Скрипт для восстановления последнего бэкапа базы данных Neon.tech

# Конфигурация подключения (твои данные)
PGPASSWORD="npg_TyadfEV31cFo"
PGHOST="ep-red-flower-aihypp35-pooler.c-4.us-east-1.aws.neon.tech"
PGUSER="neondb_owner"
PGDATABASE="neondb"
PGPORT="5432"
SSLMODE="require"

# Папка с бэкапами
BACKUP_DIR="$HOME/MRAK/backups"

# Найти последний бэкап
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/*.sql 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ Нет бэкапов в $BACKUP_DIR"
    exit 1
fi

echo "✅ Найден бэкап: $LATEST_BACKUP"
echo "🔄 Восстанавливаю..."

# Выполнить восстановление
psql "postgresql://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$PGDATABASE?sslmode=$SSLMODE" < "$LATEST_BACKUP"

if [ $? -eq 0 ]; then
    echo "✅ Восстановление успешно завершено"
else
    echo "❌ Ошибка при восстановлении"
    exit 1
fi
