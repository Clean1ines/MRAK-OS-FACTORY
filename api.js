// api.js - слой работы с сервером

async function apiFetch(url, options = {}) {
    const res = await fetch(url, options);
    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.error || `HTTP error ${res.status}`);
    }
    return res.json();
}

// Проекты
async function fetchProjects() {
    return apiFetch('/api/projects');
}

async function createProject(name, description = '') {
    return apiFetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description })
    });
}

// Артефакты
async function fetchArtifacts(projectId, type = null) {
    const url = type ? `/api/projects/${projectId}/artifacts?type=${type}` : `/api/projects/${projectId}/artifacts`;
    return apiFetch(url);
}

async function saveArtifact(projectId, artifactType, content, parentId = null, generate = false, model = null) {
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

// Универсальные эндпоинты
async function fetchLatestArtifact(parentId, artifactType) {
    return apiFetch(`/api/latest_artifact?parent_id=${encodeURIComponent(parentId)}&type=${encodeURIComponent(artifactType)}`);
}

async function generateArtifact(artifactType, parentId, feedback = '', model = null, projectId, existingContent = null) {
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

// Модели
async function fetchModels() {
    return apiFetch('/api/models');
}

// Режимы (промпты)
async function fetchModes() {
    return apiFetch('/api/modes');
}

// ADDED: получение истории сообщений
async function fetchMessages(projectId) {
    return apiFetch(`/api/projects/${projectId}/messages`);
}

// Экспортируем всё в глобальный объект api
window.api = {
    apiFetch,           // теперь apiFetch доступен как api.apiFetch
    fetchProjects,
    createProject,
    fetchArtifacts,
    saveArtifact,
    fetchLatestArtifact,
    generateArtifact,
    saveArtifactPackage,
    fetchModels,
    fetchModes,
    fetchMessages       // ADDED
};
