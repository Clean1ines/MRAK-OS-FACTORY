window.state = {
    // Берем ID напрямую из DOM, если в памяти пусто. Это самый надежный костыль.
    getCurrentProjectId() {
        const sel = document.getElementById('project-select');
        return sel ? sel.value : null;
    },
    getCurrentModel() {
        const sel = document.getElementById('model-select');
        return sel ? sel.value : 'llama-3.3-70b-versatile';
    },
    getCurrentParentId() {
        const sel = document.getElementById('parent-select');
        return sel ? sel.value : null;
    },
    getArtifactType() {
        const sel = document.getElementById('artifact-type-select');
        return sel ? sel.value : 'BusinessRequirementPackage';
    },
    setProjects(l) { this.projects = l; },
    setModels(l) { this.models = l; },
    setArtifacts(l) { this.artifacts = l; }
};
