window.api = {
    async fetchModels() {
        try {
            const r = await fetch('/api/models');
            const data = await r.json();
            console.log("DEBUG: Raw models from server:", data);
            // Если Groq возвращает структуру {data: [...]}, берем data. Если просто массив - его.
            const models = data.data || data;
            return Array.isArray(models) ? models : [];
        } catch (e) {
            console.error("DEBUG: Fetch models failed:", e);
            return [];
        }
    },
    async fetchProjects() {
        const r = await fetch('/api/projects');
        return await r.json();
    },
    async fetchArtifacts(pid) {
        const r = await fetch(`/api/projects/${pid}/artifacts`);
        return await r.json();
    },
    async generateArtifact(type, parentId, feedback, model, projectId) {
        const r = await fetch('/api/generate_artifact', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                artifact_type: type,
                parent_id: parentId,
                user_feedback: feedback,
                model_name: model,
                project_id: projectId
            })
        });
        return await r.json();
    }
};

// ===== ДИАГНОСТИКА =====
const originalFetchArtifacts = fetchArtifacts;
fetchArtifacts = async function(projectId, type) {
    console.log('[API] fetchArtifacts called', { projectId, type });
    try {
        const result = await originalFetchArtifacts(projectId, type);
        console.log('[API] fetchArtifacts response:', result);
        return result;
    } catch (e) {
        console.error('[API] fetchArtifacts error:', e);
        throw e;
    }
};

window.api.fetchArtifacts = fetchArtifacts;

// ===== ДИАГНОСТИКА: ВСЕ ФУНКЦИИ =====
const originalFetchProjects = fetchProjects;
fetchProjects = async function() {
    console.log('[API] fetchProjects START');
    try {
        const res = await originalFetchProjects();
        console.log('[API] fetchProjects SUCCESS, count:', res.length);
        return res;
    } catch (e) {
        console.error('[API] fetchProjects ERROR:', e);
        throw e;
    }
};

const originalCreateProject = createProject;
createProject = async function(name, description) {
    console.log('[API] createProject START', { name, description });
    try {
        const res = await originalCreateProject(name, description);
        console.log('[API] createProject SUCCESS, id:', res.id);
        return res;
    } catch (e) {
        console.error('[API] createProject ERROR:', e);
        throw e;
    }
};

const originalSaveArtifact = saveArtifact;
saveArtifact = async function(projectId, artifactType, content, parentId, generate, model) {
    console.log('[API] saveArtifact START', { projectId, artifactType, parentId, generate, model });
    try {
        const res = await originalSaveArtifact(projectId, artifactType, content, parentId, generate, model);
        console.log('[API] saveArtifact SUCCESS, id:', res.id);
        return res;
    } catch (e) {
        console.error('[API] saveArtifact ERROR:', e);
        throw e;
    }
};

const originalFetchLatestArtifact = fetchLatestArtifact;
fetchLatestArtifact = async function(parentId, artifactType) {
    console.log('[API] fetchLatestArtifact START', { parentId, artifactType });
    try {
        const res = await originalFetchLatestArtifact(parentId, artifactType);
        console.log('[API] fetchLatestArtifact SUCCESS, exists:', res.exists);
        return res;
    } catch (e) {
        console.error('[API] fetchLatestArtifact ERROR:', e);
        throw e;
    }
};

const originalGenerateArtifact = generateArtifact;
generateArtifact = async function(artifactType, parentId, feedback, model, projectId, existingContent) {
    console.log('[API] generateArtifact START', { artifactType, parentId, feedback, model, projectId });
    try {
        const res = await originalGenerateArtifact(artifactType, parentId, feedback, model, projectId, existingContent);
        console.log('[API] generateArtifact SUCCESS, result keys:', Object.keys(res));
        return res;
    } catch (e) {
        console.error('[API] generateArtifact ERROR:', e);
        throw e;
    }
};

const originalSaveArtifactPackage = saveArtifactPackage;
saveArtifactPackage = async function(projectId, parentId, artifactType, content) {
    console.log('[API] saveArtifactPackage START', { projectId, parentId, artifactType, contentLength: Array.isArray(content) ? content.length : 'not array' });
    try {
        const res = await originalSaveArtifactPackage(projectId, parentId, artifactType, content);
        console.log('[API] saveArtifactPackage SUCCESS, id:', res.id);
        return res;
    } catch (e) {
        console.error('[API] saveArtifactPackage ERROR:', e);
        throw e;
    }
};

const originalFetchModels = fetchModels;
fetchModels = async function() {
    console.log('[API] fetchModels START');
    try {
        const res = await originalFetchModels();
        console.log('[API] fetchModels SUCCESS, count:', res.length);
        return res;
    } catch (e) {
        console.error('[API] fetchModels ERROR:', e);
        throw e;
    }
};

// Переопределяем глобальный api
window.api = {
    fetchProjects,
    createProject,
    fetchArtifacts,
    saveArtifact,
    fetchLatestArtifact,
    generateArtifact,
    saveArtifactPackage,
    fetchModels
};
console.log('[API] файл загружен');
