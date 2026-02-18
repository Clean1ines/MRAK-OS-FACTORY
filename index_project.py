#!/usr/bin/env python3
"""
Индексирует проект: сканирует файлы (с помощью generate_tree.py) и сохраняет каждый как артефакт CodeFile в БД.
При повторном запуске проверяет изменения по хешу и обновляет артефакт, увеличивая версию.
"""

import os
import sys
import asyncio
import argparse
import hashlib
from pathlib import Path
import json
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Добавляем путь к проекту для импорта generate_tree и db
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import generate_tree
import db

# Системные директории, которые нужно игнорировать при индексации
EXCLUDED_DIRS = {
    '.git',
    '__pycache__',
    '.mypy_cache',
    '.pytest_cache',
    '.venv',
    'venv',
    'env',
    'node_modules',
    '.idea',
    '.vscode',
    'dist',
    'build',
    '*.egg-info',
}

async def index_project(project_path: str, owner: str = "system"):
    """Сканирует проект и сохраняет файлы как артефакты."""
    await db.init_db()  # убедимся, что таблицы есть

    path = Path(project_path).resolve()
    print(f"Индексация проекта {path}...")

    # Загружаем .gitignore
    gitignore_patterns = generate_tree.read_gitignore(path)
    include_patterns, exclude_patterns = generate_tree.parse_gitignore_patterns(gitignore_patterns)

    # Определяем расширения для включения
    INCLUDED_EXTENSIONS = {'.py', '.json', '.ts', '.js'}

    # Рекурсивный обход
    files_to_index = []

    def walk_dir(current_path):
        # Пропускаем системные директории по имени
        if current_path.name in EXCLUDED_DIRS:
            return
        for item in current_path.iterdir():
            # Пропускаем .git (на всякий случай)
            if item.name == '.git':
                continue
            # Проверяем gitignore
            if generate_tree.is_ignored(item.name, item, exclude_patterns, include_patterns):
                continue
            if item.is_dir():
                walk_dir(item)
            elif item.is_file() and item.suffix.lower() in INCLUDED_EXTENSIONS:
                files_to_index.append(item)

    walk_dir(path)

    print(f"Найдено {len(files_to_index)} файлов для индексации.")

    for file_path in files_to_index:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Ошибка чтения {file_path}: {e}")
            continue

        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        rel_path = str(file_path.relative_to(path))

        existing = await db.find_artifact_by_path(rel_path, "CodeFile")

        if existing:
            # Используем .get() для безопасного доступа, если ключа нет (старая запись)
            old_hash = existing.get('content_hash')
            if old_hash == content_hash:
                print(f"Файл {file_path} не изменился, пропускаем.")
                continue
            else:
                # увеличиваем версию (простая логика: увеличиваем минорную часть)
                old_version = existing['version']
                try:
                    major, minor = map(int, old_version.split('.'))
                    new_version = f"{major}.{minor + 1}"
                except:
                    new_version = "1.1"  # fallback, если версия не в формате "x.y"

                artifact_content = {
                    "file_path": rel_path,
                    "file_name": file_path.name,
                    "extension": file_path.suffix,
                    "content": content,
                    "size": len(content)
                }

                await db.update_artifact(existing['id'], artifact_content, new_version, content_hash)
                print(f"Обновлён {file_path} (версия {new_version}) -> {existing['id']}")
        else:
            # сохраняем новый артефакт
            artifact_content = {
                "file_path": rel_path,
                "file_name": file_path.name,
                "extension": file_path.suffix,
                "content": content,
                "size": len(content)
            }
            artifact_id = await db.save_artifact(
                artifact_type="CodeFile",
                content=artifact_content,
                owner=owner,
                status="INDEXED",
                version="1.0",
                content_hash=content_hash
            )
            print(f"Сохранён {file_path} -> {artifact_id}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Индексирует проект в базу знаний.")
    parser.add_argument("path", nargs="?", default=".", help="Путь к проекту")
    parser.add_argument("--owner", default="system", help="Владелец артефактов")
    args = parser.parse_args()

    asyncio.run(index_project(args.path, args.owner))
