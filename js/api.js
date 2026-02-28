// api.js - слой работы с сервером
console.log('[API] загрузка начата');

async function apiFetch(url, options = {}) {
    console.log('[API] apiFetch', url);
    const res = await fetch(url, options);
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.error || `HTTP error ${res.status}`);
    }
    return res.json();
}

// Проекты
async function fetchProjects() {
    console.log('[API] fetchProjects');
    return apiFetch('/api/projects');
}

async function createProject(name, description = '') {
    console.log('[API] createProject', { name, description });
    return apiFetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description })
    });
}

// Артефакты
async function fetchArtifacts(projectId, type = null) {
    console.log('[API] fetchArtifacts', { projectId, type });
    const url = type ? `/api/projects/${projectId}/artifacts?type=${type}` : `/api/projects/${projectId}/artifacts`;
    return apiFetch(url);
}

async function saveArtifact(projectId, artifactType, content, parentId = null, generate = false, model = null) {
    console.log('[API] saveArtifact', { projectId, artifactType, parentId, generate, model });
    return apiFetch('/api/artifact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            project_id: projectId,
            artifact_type: artifactType,
            content: content,
            parent_id: parentId,
            generate: generate,
            model: model
        })
    });
}

async function fetchLatestArtifact(parentId, artifactType) {
    console.log('[API] fetchLatestArtifact', { parentId, artifactType });
    return apiFetch(`/api/latest_artifact?parent_id=${encodeURIComponent(parentId)}&type=${encodeURIComponent(artifactType)}`);
}

async function generateArtifact(artifactType, parentId, feedback = '', model = null, projectId, existingContent = null) {
    console.log('[API] generateArtifact', { artifactType, parentId, feedback, model, projectId });
    return apiFetch('/api/generate_artifact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            artifact_type: artifactType,
            parent_id: parentId,
            feedback: feedback,
            model: model,
            project_id: projectId,
            existing_content: existingContent
        })
    });
}

async function saveArtifactPackage(projectId, parentId, artifactType, content) {
    console.log('[API] saveArtifactPackage', { projectId, parentId, artifactType, contentLength: Array.isArray(content) ? content.length : 'not array' });
    return apiFetch('/api/save_artifact_package', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            project_id: projectId,
            parent_id: parentId,
            artifact_type: artifactType,
            content: content
        })
    });
}

async function fetchModels() {
    console.log('[API] fetchModels');
    return apiFetch('/api/models');
}

// Режимы (промпты)
async function fetchModes() {
    return apiFetch('/api/modes');
}

// История сообщений
async function fetchMessages(projectId) {
    return apiFetch(`/api/projects/${projectId}/messages`);
}

// Сессии уточнения
async function startClarification(projectId, targetArtifactType, model = null) {
    return apiFetch('/api/clarification/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            project_id: projectId,
            target_artifact_type: targetArtifactType,
            model: model
        })
    });
}

async function sendClarificationMessage(sessionId, message) {
    return apiFetch(`/api/clarification/${sessionId}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
    });
}

async function getClarificationSession(sessionId) {
    return apiFetch(`/api/clarification/${sessionId}`);
}

async function completeClarificationSession(sessionId) {
    return apiFetch(`/api/clarification/${sessionId}/complete`, { method: 'POST' });
}

async function fetchActiveClarificationSessions(projectId) {
    return apiFetch(`/api/projects/${projectId}/clarification/active`);
}

// Типы артефактов
async function fetchArtifactTypes() {
    return apiFetch('/api/artifact-types');
}

async function fetchArtifactType(type) {
    return apiFetch(`/api/artifact-types/${type}`);
}

// Экспортируем всё в глобальный объект api
window.api = {
    apiFetch,
    fetchProjects,
    createProject,
    fetchArtifacts,
    saveArtifact,
    fetchLatestArtifact,
    generateArtifact,
    saveArtifactPackage,
    fetchModels,
    fetchModes,
    fetchMessages,
    startClarification,
    sendClarificationMessage,
    getClarificationSession,
    completeClarificationSession,
    fetchActiveClarificationSessions,
    fetchArtifactTypes,
    fetchArtifactType
};

console.log('[API] загрузка завершена, window.api определён:', !!window.api);

async function sendChatMessage(prompt, mode, model, projectId) {
    console.log('[API] sendChatMessage', { prompt, mode, model, projectId });
    return fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, mode, model, project_id: projectId })
    });
}

window.api.sendChatMessage = sendChatMessage;

async function sendChatMessage(prompt, mode, model, projectId) {
    console.log('[API] sendChatMessage', { prompt, mode, model, projectId });
    return fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, mode, model, project_id: projectId })
    });
}

window.api.sendChatMessage = sendChatMessage;
