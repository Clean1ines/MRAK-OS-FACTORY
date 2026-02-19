window.api = {
    async fetchModels() {
        try {
            const r = await fetch('/api/models');
            const data = await r.json();
            // Groq возвращает { data: [{id: "..."}] } или просто массив
            return Array.isArray(data) ? data : (data.data || []);
        } catch (e) {
            console.error("Model fetch failed", e);
            return [{id: "llama-3.3-70b-versatile"}, {id: "llama-3.1-8b-instant"}];
        }
    },
    async fetchProjects() {
        const r = await fetch('/api/projects');
        return await r.json();
    },
    async fetchArtifacts(pid) {
        if (!pid) return [];
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
        if (!r.ok) throw new Error("API Error");
        return await r.json();
    }
};
