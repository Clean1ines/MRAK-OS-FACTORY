// state.js - управление состоянием приложения

const AppState = {
    projects: [],
    currentProjectId: localStorage.getItem('selectedProjectId') || '',
    artifacts: [],
    parentData: {}, // id -> type
    currentArtifact: null, // текущий редактируемый артефакт (для модалки)
    currentParentId: null,
    models: [],
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

// Сеттеры
function setProjects(projects) {
    AppState.projects = projects;
    notify();
}

function setCurrentProjectId(id) {
    AppState.currentProjectId = id;
    if (id) localStorage.setItem('selectedProjectId', id);
    else localStorage.removeItem('selectedProjectId');
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

// Конфигурация генерации: для каждого типа дочернего артефакта список допустимых родительских типов
const generationRules = {
    "BusinessRequirementPackage": ["ProductCouncilAnalysis"],
    "FunctionalRequirementPackage": ["BusinessRequirementPackage", "ReqEngineeringAnalysis"],
    // Добавляйте другие типы по мере необходимости
};

function canGenerate(childType, parentType) {
    const allowedParents = generationRules[childType];
    return allowedParents ? allowedParents.includes(parentType) : false;
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
    setArtifactCache,
    getArtifactCache,
    clearArtifactCache,
    subscribe,
};

// Добавляем правило для анализа инженерии требований
generationRules["ReqEngineeringAnalysis"] = ["BusinessRequirementPackage"];

// Убедимся, что правило для ReqEngineeringAnalysis есть
generationRules["ReqEngineeringAnalysis"] = ["BusinessRequirementPackage"];
