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
