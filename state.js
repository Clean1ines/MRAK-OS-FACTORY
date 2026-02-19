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
    // обновляем parentData
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
    subscribe,
};

let currentParentId = null;

function setCurrentParentId(id) {
    currentParentId = id;
}

function getCurrentParentId() {
    return currentParentId;
}

window.state.setCurrentParentId = setCurrentParentId;
window.state.getCurrentParentId = getCurrentParentId;
