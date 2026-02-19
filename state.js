// state.js - управление состоянием приложения

const AppState = {
    projects: [],
    currentProjectId: localStorage.getItem('selectedProjectId') || '',
    artifacts: [],
    parentData: {}, // id -> type
    currentRequirements: [],
    currentAnalysisId: null,
    currentFeedback: '',
    models: [],
    currentParentId: null,
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
function getCurrentRequirements() { return AppState.currentRequirements; }
function getCurrentAnalysisId() { return AppState.currentAnalysisId; }
function getCurrentFeedback() { return AppState.currentFeedback; }
function getModels() { return AppState.models; }
function getCurrentParentId() { return AppState.currentParentId; }

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

function setCurrentRequirements(req) {
    AppState.currentRequirements = req;
    notify();
}

function setCurrentAnalysisId(id) {
    AppState.currentAnalysisId = id;
}

function setCurrentFeedback(fb) {
    AppState.currentFeedback = fb;
}

function setModels(models) {
    AppState.models = models;
    notify();
}

function setCurrentParentId(id) {
    AppState.currentParentId = id;
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
    getCurrentRequirements,
    setCurrentRequirements,
    getCurrentAnalysisId,
    setCurrentAnalysisId,
    getCurrentFeedback,
    setCurrentFeedback,
    getModels,
    setModels,
    getCurrentParentId,
    setCurrentParentId,
    subscribe,
};

// Пакетный кеш (parentId -> { package_id, requirements })
let packageCache = {};

function setPackageCache(parentId, data) {
    packageCache[parentId] = data;
}

function getPackageCache(parentId) {
    return packageCache[parentId];
}

function clearPackageCache(parentId) {
    if (parentId) delete packageCache[parentId];
    else packageCache = {};
}

window.state.setPackageCache = setPackageCache;
window.state.getPackageCache = getPackageCache;
window.state.clearPackageCache = clearPackageCache;
