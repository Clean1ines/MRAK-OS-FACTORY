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

// Генерация бизнес-требований
async function generateBusinessRequirements(analysisId, feedback = '', model = null, projectId) {
    return apiFetch('/api/generate_business_requirements', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            analysis_id: analysisId,
            feedback: feedback,
            model: model,
            project_id: projectId
        })
    });
}

async function saveBusinessRequirements(projectId, parentId, requirements) {
    return apiFetch('/api/save_business_requirements', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            project_id: projectId,
            parent_id: parentId,
            requirements: requirements
        })
    });
}

// Модели
async function fetchModels() {
    return apiFetch('/api/models');
}

// Делаем функции глобальными (для обратной совместимости)
window.api = {
    fetchProjects,
    createProject,
    fetchArtifacts,
    saveArtifact,
    generateBusinessRequirements,
    saveBusinessRequirements,
    fetchModels
};
