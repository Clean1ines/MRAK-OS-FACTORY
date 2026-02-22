// state.js - управление состоянием приложения

const AppState = {
    projects: [],
    currentProjectId: localStorage.getItem('selectedProjectId') || '',
    artifacts: [],
    parentData: {}, // id -> type
    currentArtifact: null, // текущий редактируемый артефакт (для модалки)
    currentParentId: null,
    models: [],
    // ADDED: текущая сессия уточнения в расширенном режиме
    currentClarificationSessionId: null,
};

const listeners = [];

function subscribe(listener) {
    listeners.push(listener);
}

function notify() {
    listeners.forEach(fn => fn());
}

// Геттеры
function getProjects() { return AppState.projects; }
function getCurrentProjectId() { return AppState.currentProjectId; }
function getArtifacts() { return AppState.artifacts; }
function getParentData() { return AppState.parentData; }
function getCurrentArtifact() { return AppState.currentArtifact; }
function getCurrentParentId() { return AppState.currentParentId; }
function getModels() { return AppState.models; }
// ADDED
function getCurrentClarificationSessionId() { return AppState.currentClarificationSessionId; }

// Сеттеры
function setProjects(projects) {
    AppState.projects = projects;
    notify();
}

function setCurrentProjectId(id) {
    AppState.currentProjectId = id;
    if (id) localStorage.setItem('selectedProjectId', id);
    else localStorage.removeItem('selectedProjectId');
    // ADDED: при смене проекта сбрасываем текущую сессию
    AppState.currentClarificationSessionId = null;
    notify();
}

function setArtifacts(artifacts) {
    AppState.artifacts = artifacts;
    const newParentData = {};
    artifacts.forEach(a => { newParentData[a.id] = a.type; });
    AppState.parentData = newParentData;
    notify();
}

function setCurrentArtifact(artifact) {
    AppState.currentArtifact = artifact;
    notify();
}

function setCurrentParentId(id) {
    AppState.currentParentId = id;
}

function setModels(models) {
    AppState.models = models;
    notify();
}

// ADDED
function setCurrentClarificationSessionId(id) {
    AppState.currentClarificationSessionId = id;
    notify();
}

// Конфигурация генерации: для каждого типа дочернего артефакта список допустимых родительских типов
const generationRules = {
    "BusinessRequirementPackage": ["ProductCouncilAnalysis"],
    "ReqEngineeringAnalysis": ["BusinessRequirementPackage"],
    "FunctionalRequirementPackage": ["ReqEngineeringAnalysis"],
    "ArchitectureAnalysis": ["FunctionalRequirementPackage"],
    "AtomicTask": ["ArchitectureAnalysis"],
    "CodeArtifact": ["AtomicTask"],
    "TestPackage": ["CodeArtifact"],
};

function canGenerate(childType, parentType) {
    const allowedParents = generationRules[childType];
    return allowedParents ? allowedParents.includes(parentType) : false;
}

function getAllowedParentTypes(childType) {
    return generationRules[childType] || [];
}

// ADDED: список типов артефактов, требующих уточнения (для расширенного режима)
const CLARIFICATION_TYPES = [
    "BusinessIdea",
    "ProductCouncilAnalysis",
    // при необходимости можно добавить другие
];

function requiresClarification(artifactType) {
    return CLARIFICATION_TYPES.includes(artifactType);
}

// Кеш для артефактов (parentId -> { childType: { id, content } })
let artifactCache = {};

function setArtifactCache(parentId, childType, data) {
    if (!artifactCache[parentId]) artifactCache[parentId] = {};
    artifactCache[parentId][childType] = data;
}

function getArtifactCache(parentId, childType) {
    return artifactCache[parentId]?.[childType];
}

function clearArtifactCache(parentId, childType) {
    if (parentId && childType) {
        if (artifactCache[parentId]) delete artifactCache[parentId][childType];
    } else if (parentId) {
        delete artifactCache[parentId];
    } else {
        artifactCache = {};
    }
}

// Новая функция: получить последний артефакт по типу (среди всех проектов или для текущего проекта)
function getLastArtifactByType(type, projectId = AppState.currentProjectId) {
    if (!projectId) return null;
    // Фильтруем артефакты по проекту и типу, сортируем по created_at, берём последний
    const filtered = AppState.artifacts.filter(a => a.type === type && a.status === 'VALIDATED');
    if (filtered.length === 0) return null;
    // Сортировка по created_at (новые сверху)
    filtered.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    return filtered[0];
}

// Экспортируем в глобальную область
window.state = {
    getProjects,
    setProjects,
    getCurrentProjectId,
    setCurrentProjectId,
    getArtifacts,
    setArtifacts,
    getParentData,
    getCurrentArtifact,
    setCurrentArtifact,
    getCurrentParentId,
    setCurrentParentId,
    getModels,
    setModels,
    canGenerate,
    getAllowedParentTypes,
    setArtifactCache,
    getArtifactCache,
    clearArtifactCache,
    getLastArtifactByType,
    subscribe,
    // ADDED
    getCurrentClarificationSessionId,
    setCurrentClarificationSessionId,
    requiresClarification
};
