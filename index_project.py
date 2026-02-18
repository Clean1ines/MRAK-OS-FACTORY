#!/usr/bin/env python3
"""
Индексирует проект: сканирует файлы (с помощью generate_tree.py) и сохраняет каждый как артефакт CodeFile в БД.
Используется для фазы 5.2.
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
import json

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

        # Формируем артефакт CodeFile
        artifact_content = {
            "file_path": str(file_path.relative_to(path)),
            "file_name": file_path.name,
            "extension": file_path.suffix,
            "content": content,
            "size": len(content)
        }

        # Сохраняем в БД
        artifact_id = await db.save_artifact(
            artifact_type="CodeFile",
            content=artifact_content,
            owner=owner,
            status="INDEXED"
        )
        print(f"Сохранён {file_path} -> {artifact_id}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Индексирует проект в базу знаний.")
    parser.add_argument("path", nargs="?", default=".", help="Путь к проекту")
    parser.add_argument("--owner", default="system", help="Владелец артефактов")
    args = parser.parse_args()

    asyncio.run(index_project(args.path, args.owner))
