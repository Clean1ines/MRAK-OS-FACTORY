Architecture & Structure Guide: MRAK-OS-FACTORY

Standard: Feature-Sliced Design (FSD)
Last Updated: 2026-03-02
Status: Phase 1 (Shared) Completed.
1. Global Aliases

Проект использует Path Aliases для исключения относительных путей ../../.

    @app/* -> src/app/*

    @pages/* -> src/pages/*

    @widgets/* -> src/widgets/*

    @features/* -> src/features/*

    @entities/* -> src/entities/*

    @shared/* -> src/shared/*

2. Layer: Shared

Самый нижний слой. Не имеет зависимостей от других слоев проекта. Содержит переиспользуемую логику и UI-примитивы.
📂 shared/api (Сетевой слой)

    EntryPoint: @shared/api

    Contents:

        client.ts: Основной инстанс API (Axios/Fetch).

        fetchWithTimeout.ts: Утилита для запросов с лимитом времени.

        queryClient.ts: Конфигурация TanStack Query.

        generated/schema.ts: Автогенерированные типы бэкенда.

📂 shared/ui (UI-кит)

    EntryPoint: @shared/ui

    Components:

        modal/BaseModal: Основа для всех всплывающих окон.

        modal/DeleteConfirmModal: Универсальное окно подтверждения удаления.

        toast/Toast: Система уведомлений.

📂 shared/lib (Infrastructure & Types)

    EntryPoint: @shared/lib

    Contents:

        types.ts: Source of Truth для базовых структур данных (например, NodeData, EdgeData).

        graphUtils.ts: Математика графов (циклы, валидация).

        logger.ts: Глобальный логгер.

        deterministicRandom.ts: Генератор предсказуемого рандома.

3. Правила импортов (Cross-boundary rules)

    Запрещено: Импортировать что-либо из src/hooks/* или src/components/* внутрь src/shared/*.

    Рекомендуется: Все импорты из Shared делать через публичный API (алиас), например:
    import { NodeData } from '@shared/lib'; вместо относительных путей.

Сущность Project

Теперь, когда мы декомпозировали проекты, правила взаимодействия выглядят так:
Файл / Слой	Ответственность
src/entities/project/model/types.ts	Источник истины для типа Project и интерфейса стора.
src/entities/project/model/slice.ts	Управление состоянием (список, текущий ID) и Persistence (localStorage).
src/entities/project/index.ts	Public API сущности. Все внешние слои импортируют только отсюда.
src/hooks/useProjects.ts	Фасад для работы с API и синхронизации стора с сервером.
2. Текущее состояние useAppStore

Мы значительно облегчили useAppStore.ts. Сейчас он содержит:

    Artifacts: Состояние и методы управления артефактами.

    Messages: История чата.

    Models/Modes: Настройки текущей сессии ИИ.

    UI State: Простые флаги (simple mode, токены).


1. Слой: Shared (Инфраструктура и UI-кит)

Зависимости: Нет.
Старый путь	Путь в FSD (@shared)	Почему?
src/api/*	api/*	Весь транспорт (Axios, Fetch).
src/shared/api/*	api/*	(Уже там) client, queryClient.
src/hooks/useStreaming.ts	api/streaming.ts	SSE-транспорт — это низкоуровневая сетевая логика.
src/assets/react.svg	assets/react.svg	Статика.
src/constants/canvas.ts	lib/constants/canvas.ts	Математика и константы холста.
src/hooks/useMediaQuery.ts	lib/hooks/useMediaQuery.ts	Браузерный хелпер.
src/hooks/useNotifications.ts	lib/notification/useNotifications.ts	Хук-адаптер для уведомлений.
src/components/Notification.tsx	ui/toast/Notification.tsx	Атомарный UI для алертов.
src/shared/ui/*	ui/*	(Уже там) Модалки и Тосты.
src/shared/lib/*	lib/*	(Уже там) graphUtils, logger, deterministicRandom.
src/styles/ThemeEffects.tsx	ui/theme/ThemeEffects.tsx	Глобальные визуальные эффекты.
src/utils/*	lib/utils/*	Хелперы общего назначения.
2. Слой: Entities (Сущности и Слайсы Стора)

Зависимости: Shared. Содержит слайсы, которые импортируются в src/app/store.
Старый путь / Слайс	Путь в FSD (@entities)	Почему?
Auth State (Token/User)	session/model/session.slice.ts	Стейт авторизации (сессия).
useAppStore.ts (messages)	chat/model/chat.slice.ts	Слайс сообщений.
useAppStore.ts (artifacts)	artifact/model/artifact.slice.ts	Слайс артефактов.
useAppStore.ts (models/modes)	ai-config/model/config.slice.ts	Настройки ИИ моделей.
src/entities/project/*	project/*	(Уже там) Логика проектов.
src/components/ChatMessage.tsx	chat/ui/ChatMessage.tsx	Отображение сообщения.
src/components/ios/IOSNode.tsx	node/ui/Node.tsx	Визуал узла графа.
src/components/ios/useNodeValidation.ts	node/lib/validation.ts	Валидация данных узла.
src/hooks/useMessages.ts	chat/api/useMessages.ts	API-запросы чата.
src/hooks/useArtifacts.ts	artifact/api/useArtifacts.ts	API-запросы артефактов.
src/hooks/useArtifactTypes.ts	artifact/api/useArtifactTypes.ts	Справочник типов артефактов.
src/hooks/useModels.ts	ai-config/api/useModels.ts	API-запросы моделей.
src/hooks/useModes.ts	ai-config/api/useModes.ts	API-запросы режимов.
src/hooks/useWorkflows.ts	workflow/api/useWorkflows.ts	Список воркфлоу.
3. Слой: Features (Действия / Фичи)

Зависимости: Shared, Entities. То, что меняет состояние.
Старый путь	Путь в FSD (@features)	Почему?
src/components/auth/AuthGuard.tsx	auth/protect-routes	Защита маршрутов.
src/hooks/useSendMessage.ts	chat/send-message	Логика "взять текст -> отправить -> стримить".
src/components/projects/CreateProjectModal.tsx	project/create	Фича создания проекта.
src/components/projects/EditProjectModal.tsx	project/edit	Фича редактирования проекта.
src/components/ios/CreateWorkflowModal.tsx	workflow/create	Создание холста.
src/components/ios/EditWorkflowModal.tsx	workflow/edit	Редактирование метаданных холста.
src/components/ios/EditNodeModal.tsx	node/edit-content	Редактирование данных внутри ноды.
src/components/ios/NodeModal.tsx	node/view-details	Просмотр подробностей ноды.
4. Слой: Widgets (Сложные блоки)

Зависимости: Shared, Entities, Features. Сборка компонентов.
Старый путь	Путь в FSD (@widgets)	Почему?
src/components/layout/ProtectedLayout.tsx	layout/ProtectedLayout.tsx	Глобальный каркас страницы.
src/components/layout/HamburgerMenu.tsx	header/HamburgerMenu.tsx	Верхняя панель.
src/components/projects/ProjectsSidebar.tsx	sidebar/ProjectsSidebar.tsx	Боковая панель управления.
src/components/ChatCanvas.tsx	chat-panel/ChatCanvas.tsx	Панель чата.
src/components/ChatInterface.tsx	chat-window/ChatInterface.tsx	Окно чата в сборе.
src/components/ios/IOSCanvas.tsx	workflow-editor	Главный виджет редактора.
src/components/ios/IOSShell.tsx	workflow-shell	Оболочка редактора.
src/components/ios/NodeListPanel.tsx	node-picker	Панель выбора нод.
src/components/ios/WorkflowHeader.tsx	workflow-header	Хедер конкретного воркфлоу.
src/hooks/useCanvasEngine.ts	workflow-editor/lib/useCanvasEngine.ts	"Мозг" React Flow холста.
src/hooks/useWorkflowCanvas.ts	workflow-editor/lib/useWorkflowCanvas.ts	Интеграция данных воркфлоу с холстом.
5. Слои: Pages & App

    Pages:

        src/components/auth/LoginPage.tsx -> @pages/login

        src/components/ios/WorkspacePage.tsx -> @pages/workspace

    App:

        src/App.tsx -> src/app/App.tsx

        src/main.tsx -> src/app/main.tsx

        src/index.css -> src/app/styles/index.css

        src/store/useAppStore.ts -> src/app/store/index.ts (Агрегатор слайсов).

        src/test/setup.ts -> src/app/test/setup.ts

Тесты и E2E

    Unit/Hook Tests: src/hooks/__tests__/*, src/constants/__tests__/* и другие переезжают внутрь соответствующих папок в FSD (рядом с файлом, который они тестят).

    E2E Tests: ./tests/e2e остаются на месте (вне src), так как это внешнее тестирование.