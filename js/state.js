// state.js - управление состоянием приложения
console.log('[STATE] загрузка начата');

const AppState = {
    projects: [],
    currentProjectId: localStorage.getItem('selectedProjectId') || '',
    artifacts: [],
    parentData: {},
    currentArtifact: null,
    currentParentId: null,
    models: [],
    // ADDED: текущая сессия уточнения в расширенном режиме
    currentClarificationSessionId: null,
    // ADDED: загруженные типы артефактов из БД
    artifactTypes: [],
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
function getCurrentClarificationSessionId() { return AppState.currentClarificationSessionId; }
// ADDED
function getArtifactTypes() { return AppState.artifactTypes; }

function setProjects(projects) { console.log('[STATE] setProjects', projects.length); AppState.projects = projects; notify(); }
function setCurrentProjectId(id) { 
    console.log('[STATE] setCurrentProjectId', id); 
    AppState.currentProjectId = id; 
    if (id) localStorage.setItem('selectedProjectId', id);
    else localStorage.removeItem('selectedProjectId');
    AppState.currentClarificationSessionId = null;
    notify();
}
function setArtifacts(artifacts) { 
    console.log('[STATE] setArtifacts', artifacts.length, artifacts[0]?.type); 
    AppState.artifacts = artifacts; 
    const newParentData = {};
    artifacts.forEach(a => { newParentData[a.id] = a.type; });
    AppState.parentData = newParentData;
    notify(); 
}
function setCurrentArtifact(artifact) { console.log('[STATE] setCurrentArtifact', artifact ? artifact.id : 'null'); AppState.currentArtifact = artifact; notify(); }
function setCurrentParentId(id) { console.log('[STATE] setCurrentParentId', id); AppState.currentParentId = id; }
function setModels(models) { console.log('[STATE] setModels', models.length); AppState.models = models; notify(); }

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

function setCurrentClarificationSessionId(id) {
    AppState.currentClarificationSessionId = id;
    notify();
}

// ADDED
function setArtifactTypes(types) {
    AppState.artifactTypes = types;
    notify();
}

// Вспомогательные функции на основе загруженных типов
function getAllowedParentTypes(childType) {
    const typeInfo = AppState.artifactTypes.find(t => t.type === childType);
    return typeInfo ? typeInfo.allowed_parents : [];
}

function requiresClarification(artifactType) {
    const typeInfo = AppState.artifactTypes.find(t => t.type === artifactType);
    return typeInfo ? typeInfo.requires_clarification : false;
}

// Для обратной совместимости (пока данные не загружены)
function canGenerate(childType, parentType) {
    const allowed = getAllowedParentTypes(childType);
    return allowed.includes(parentType);
}

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

function getLastArtifactByType(type, projectId = AppState.currentProjectId) {
    if (!projectId) return null;
    const filtered = AppState.artifacts.filter(a => a.type === type && a.status === 'VALIDATED');
    if (filtered.length === 0) return null;
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
    getCurrentClarificationSessionId,
    setCurrentClarificationSessionId,
    getArtifactTypes,
    setArtifactTypes,
    getAllowedParentTypes,
    requiresClarification,
    canGenerate,
    setArtifactCache,
    getArtifactCache,
    clearArtifactCache,
    getLastArtifactByType,
    subscribe,
};

console.log('[STATE] загрузка завершена, setCurrentProjectId есть:', typeof window.state.setCurrentProjectId);
