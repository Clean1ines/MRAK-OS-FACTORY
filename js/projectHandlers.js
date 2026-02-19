(function() {
    const projectSelect = document.getElementById("project-select");
    const modelSelect = document.getElementById("model-select");

    window.loadModels = async function() {
        if (!modelSelect) return;
        const models = await api.fetchModels();
        state.setModels(models);
        modelSelect.innerHTML = models.map(m => {
            const id = typeof m === 'string' ? m : m.id;
            return `<option value="${id}" ${id.includes('3.3-70b') ? 'selected' : ''}>${id}</option>`;
        }).join('');
    };

    window.loadParents = async function() {
        const pid = state.getCurrentProjectId();
        if (!pid) return;
        const artifacts = await api.fetchArtifacts(pid);
        state.setArtifacts(artifacts);
        const type = document.getElementById("artifact-type-select").value;
        if (window.renderers) renderers.renderParentSelect(artifacts, state.getParentData(), null, type);
    };

    if (projectSelect) {
        // Убираем старые слушатели и вешаем один рабочий
        projectSelect.onchange = async function() {
            const pid = this.value;
            console.log("Switching to project:", pid);
            state.setCurrentProjectId(pid);
            if (pid) {
                await window.loadParents();
            }
        };
    }
    
    // Инициализация загрузки проектов
    window.loadProjects = async function() {
        const projects = await api.fetchProjects();
        state.setProjects(projects);
        if (window.renderers) renderers.renderProjectSelect(projects, state.getCurrentProjectId());
    };
})();
