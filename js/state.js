// state.js - управление состоянием приложения

const AppState = {
    projects: [],
    currentProjectId: localStorage.getItem('selectedProjectId') || '',
    artifacts: [],
    parentData: {}, // id -> type
    currentArtifact: null,
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
function getProjects() { console.log('[STATE] getProjects'); return AppState.projects; }
function getCurrentProjectId() { console.log('[STATE] getCurrentProjectId'); return AppState.currentProjectId; }
function getArtifacts() { console.log('[STATE] getArtifacts'); return AppState.artifacts; }
function getParentData() { console.log('[STATE] getParentData'); return AppState.parentData; }
function getCurrentArtifact() { console.log('[STATE] getCurrentArtifact'); return AppState.currentArtifact; }
function getCurrentParentId() { console.log('[STATE] getCurrentParentId'); return AppState.currentParentId; }
function getModels() { console.log('[STATE] getModels'); return AppState.models; }

// Сеттеры
function setProjects(projects) { console.log('[STATE] setProjects', projects.length); AppState.projects = projects; notify(); }
function setCurrentProjectId(id) { 
    console.log('[STATE] setCurrentProjectId', id); 
    AppState.currentProjectId = id; 
    if (id) localStorage.setItem('selectedProjectId', id);
    else localStorage.removeItem('selectedProjectId');
    notify(); 
}
function setArtifacts(artifacts) { 
    console.log('[STATE] setArtifacts', artifacts.length, artifacts[0] ? artifacts[0].type : 'empty'); 
    AppState.artifacts = artifacts; 
    const newParentData = {};
    artifacts.forEach(a => { newParentData[a.id] = a.type; });
    AppState.parentData = newParentData;
    notify(); 
}
function setCurrentArtifact(artifact) { console.log('[STATE] setCurrentArtifact', artifact ? artifact.id : 'null'); AppState.currentArtifact = artifact; notify(); }
function setCurrentParentId(id) { console.log('[STATE] setCurrentParentId', id); AppState.currentParentId = id; }
function setModels(models) { console.log('[STATE] setModels', models.length); AppState.models = models; notify(); }

// Конфигурация генерации
const generationRules = {
    "BusinessRequirementPackage": ["ProductCouncilAnalysis"],
    "ReqEngineeringAnalysis": ["BusinessRequirementPackage"],
    "FunctionalRequirementPackage": ["ReqEngineeringAnalysis"],
};

function canGenerate(childType, parentType) {
    const allowedParents = generationRules[childType];
    return allowedParents ? allowedParents.includes(parentType) : false;
}

function getAllowedParentTypes(childType) {
    return generationRules[childType] || [];
}

// Кеш для артефактов
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
    subscribe,
};

console.log('[STATE] window.state инициализирован, setCurrentProjectId есть:', typeof window.state.setCurrentProjectId);
