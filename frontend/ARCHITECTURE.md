# Architecture & Structure Guide: MRAK-OS-FACTORY

**Standard:** Feature-Sliced Design (FSD)
**Last Updated:** 2026-03-03
**Status:** Phase 2 (Entities & Store Splitting) Completed.

## 1. Global Aliases
Проект использует Path Aliases для исключения относительных путей:
- `@app/*` -> `src/app/*` (Composition layer: store, entry point)
- `@pages/*` -> `src/pages/*`
- `@widgets/*` -> `src/widgets/*`
- `@features/*` -> `src/features/*`
- `@entities/*` -> `src/entities/*` (Business logic & data)
- `@shared/*` -> `src/shared/*` (Infrastructure)

## 2. Layer: App (@app)
Слой инициализации и композиции.
- **Entry Point**: `src/app/main.tsx` (перенесено из корня).
- **Global Store**: `src/app/store/index.ts` — теперь это точка сборки. Он объединяет слайсы из разных сущностей (`artifact.slice`, `chat.slice`, и т.д.) в единый `useAppStore`.

## 3. Layer: Entities (@entities)
Бизнес-сущности. Каждая имеет свою модель (состояние), API и UI.

### 📂 entities/project
- Управление текущим проектом.

### 📂 entities/artifact
- **Model**: `artifact.slice.ts` (хранение списка и текущего артефакта).
- **API**: `useArtifacts.ts` (загрузка данных).

### 📂 entities/chat
- **Model**: `chat.slice.ts` (сообщения).
- **API**: `useMessages.ts`.
- **UI**: `ChatMessage.tsx` (компонент отображения).

### 📂 entities/ai-config
- Управление моделями и режимами (Model/Mode).

### 📂 entities/canvas
- **UI**: `IOSNode.tsx` (визуальное представление узла графа).

## 4. Состояние Store (Refactored)
Старый файл `src/store/useAppStore.ts` теперь является **Proxy**. 
Все новые фичи должны импортировать стор либо из `@app/store`, либо (лучше) напрямую использовать селекторы к конкретным сущностям.

## 5. Правила импортов
1. **App** может импортировать всё.
2. **Entities** могут импортировать только из **Shared**.
3. **Shared** не может импортировать ничего из верхних слоев.
