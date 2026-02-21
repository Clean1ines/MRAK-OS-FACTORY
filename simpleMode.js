// simpleMode.js - логика простого режима, прогресс-бара и кнопки "Далее"

// Состояние простого режима
let isSimpleMode = false;

// Маппинг этапов на типы артефактов (последний валидированный артефакт определяет этап)
const stageToArtifactType = {
    'idea': 'StructuredIdea',
    'requirements': 'FunctionalRequirementPackage',
    'architecture': 'ArchitectureAnalysis',
    'code': 'CodeArtifact',
    'tests': 'TestPackage'
};

// Определение текущего этапа на основе последнего валидированного артефакта
function determineCurrentStage(projectId) {
    const artifacts = state.getArtifacts(); // предполагается, что state.getArtifacts() возвращает все артефакты проекта
    // Сортируем по дате создания (новые сверху)
    const sorted = artifacts.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    for (let artifact of sorted) {
        if (artifact.status === 'VALIDATED') {
            // Сопоставляем тип с этапом
            if (artifact.type === 'StructuredIdea') return 'idea';
            if (artifact.type === 'FunctionalRequirementPackage') return 'requirements';
            if (artifact.type === 'ArchitectureAnalysis') return 'architecture';
            if (artifact.type === 'CodeArtifact') return 'code';
            if (artifact.type === 'TestPackage') return 'tests';
        }
    }
    return 'idea'; // По умолчанию – идея
}

// Обновление прогресс-бара
function renderProgressBar(currentStage) {
    const container = document.getElementById('progress-bar-container');
    if (!container) return;
    container.classList.remove('hidden');
    const steps = ['idea', 'requirements', 'architecture', 'code', 'tests'];
    const stepElements = document.querySelectorAll('.progress-step');
    stepElements.forEach(el => {
        const step = el.dataset.step;
        el.classList.remove('active', 'completed');
        if (step === currentStage) {
            el.classList.add('active');
        } else if (steps.indexOf(step) < steps.indexOf(currentStage)) {
            el.classList.add('completed');
        }
    });
}

// Обработчик кнопки "Далее"
async function handleNext() {
    const projectId = state.getCurrentProjectId();
    if (!projectId) {
        ui.showNotification('Сначала выберите проект', 'error');
        return;
    }
    const currentStage = determineCurrentStage(projectId);
    let nextStage = null;
    const stages = ['idea', 'requirements', 'architecture', 'code', 'tests'];
    const index = stages.indexOf(currentStage);
    if (index < stages.length - 1) {
        nextStage = stages[index + 1];
    } else {
        ui.showNotification('Проект завершён, нет следующего этапа', 'info');
        return;
    }

    // Определяем, какой промпт запустить и какой родительский артефакт использовать
    let parentArtifact = null;
    let promptType = null;
    switch (nextStage) {
        case 'requirements':
            // Ищем последний валидированный StructuredIdea или ProductCouncilAnalysis?
            // По логике, после идеи идёт ProductCouncilAnalysis, но в простом режиме мы можем сразу запускать генерацию бизнес-требований.
            // Для простоты возьмём последний ProductCouncilAnalysis.
            parentArtifact = state.getLastArtifactByType('ProductCouncilAnalysis');
            if (!parentArtifact) {
                ui.showNotification('Нет анализа продуктового совета', 'error');
                return;
            }
            promptType = 'BusinessRequirementPackage';
            break;
        case 'architecture':
            parentArtifact = state.getLastArtifactByType('FunctionalRequirementPackage');
            if (!parentArtifact) {
                ui.showNotification('Нет функциональных требований', 'error');
                return;
            }
            promptType = 'ReqEngineeringAnalysis'; // Сначала QA? Но мы пропустим QA для простоты
            // Лучше сразу запускать архитектуру? По логике, после требований идёт QA, потом архитектура.
            // Но для MVP можно упростить.
            promptType = 'ArchitectureAnalysis'; // Прямо архитектура
            break;
        case 'code':
            parentArtifact = state.getLastArtifactByType('ArchitectureAnalysis');
            if (!parentArtifact) {
                ui.showNotification('Нет архитектурного анализа', 'error');
                return;
            }
            promptType = 'AtomicTask'; // Atomic Code Task Generator
            break;
        case 'tests':
            parentArtifact = state.getLastArtifactByType('CodeArtifact');
            if (!parentArtifact) {
                ui.showNotification('Нет кода для тестирования', 'error');
                return;
            }
            promptType = 'TestPackage';
            break;
        default:
            ui.showNotification('Неизвестный этап', 'error');
            return;
    }

    // Вызываем генерацию через универсальную функцию
    try {
        const data = await api.generateArtifact(promptType, parentArtifact.id, '', modelSelect.value, projectId, null);
        // Показываем результат в модальном окне
        ui.openRequirementsModal(promptType, data.result, async () => {
            // Обработчик сохранения
            const saved = await api.saveArtifactPackage(projectId, parentArtifact.id, promptType, data.result);
            ui.showNotification(`Сохранён ${promptType}, ID: ${saved.id}`, 'success');
            ui.closeModal();
            // Обновляем прогресс
            const newStage = determineCurrentStage(projectId);
            renderProgressBar(newStage);
        }, () => {
            // Обработчик догенерации (пока не реализуем, можно просто перегенерировать)
            ui.showNotification('Догенерация пока не поддерживается', 'info');
        }, () => { ui.closeModal(); });
    } catch (e) {
        ui.showNotification('Ошибка генерации: ' + e.message, 'error');
    }
}

// Переключение режимов
function switchMode(mode) {
    isSimpleMode = (mode === 'simple');
    const simpleControls = document.getElementById('simple-controls');
    const advancedControls = document.getElementById('advanced-controls');
    const simpleBtn = document.getElementById('simple-mode-btn');
    const advancedBtn = document.getElementById('advanced-mode-btn');

    if (isSimpleMode) {
        simpleControls.classList.remove('hidden');
        advancedControls.classList.add('hidden');
        simpleBtn.classList.add('bg-cyan-600/30');
        advancedBtn.classList.remove('bg-cyan-600/30');
        // Показываем прогресс-бар
        document.getElementById('progress-bar-container').classList.remove('hidden');
        // Обновляем прогресс
        const projectId = state.getCurrentProjectId();
        if (projectId) {
            const stage = determineCurrentStage(projectId);
            renderProgressBar(stage);
        }
    } else {
        simpleControls.classList.add('hidden');
        advancedControls.classList.remove('hidden');
        advancedBtn.classList.add('bg-cyan-600/30');
        simpleBtn.classList.remove('bg-cyan-600/30');
        // Прогресс-бар можно скрыть или оставить – решим скрыть
        document.getElementById('progress-bar-container').classList.add('hidden');
    }
}

// Инициализация
function initSimpleMode() {
    const simpleBtn = document.getElementById('simple-mode-btn');
    const advancedBtn = document.getElementById('advanced-mode-btn');
    const nextBtn = document.getElementById('next-btn');

    if (simpleBtn) {
        simpleBtn.addEventListener('click', () => switchMode('simple'));
    }
    if (advancedBtn) {
        advancedBtn.addEventListener('click', () => switchMode('advanced'));
    }
    if (nextBtn) {
        nextBtn.addEventListener('click', handleNext);
    }
    // По умолчанию – расширенный режим
    switchMode('advanced');
}

// Экспортируем в глобальную область
window.simpleMode = {
    init: initSimpleMode,
    switchMode,
    renderProgressBar,
    determineCurrentStage,
    handleNext
};
