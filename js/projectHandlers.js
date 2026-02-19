(function() {
    const projectSelect = document.getElementById("project-select");
    const artifactTypeSelect = document.getElementById("artifact-type-select");

    // Загрузка списка проектов
    window.loadProjects = async function() {
        try {
            const projects = await api.fetchProjects();
            state.setProjects(projects);
            if (window.renderers) renderers.renderProjectSelect(projects, state.getCurrentProjectId());
        } catch (e) { console.error("Projects load error:", e); }
    };

    // Загрузка родителей (артефактов) для выбранного проекта
    window.loadParents = async function() {
        const pid = state.getCurrentProjectId();
        if (!pid) return;
        try {
            const artifacts = await api.fetchArtifacts(pid);
            state.setArtifacts(artifacts);
            const childType = artifactTypeSelect ? artifactTypeSelect.value : 'BusinessRequirementPackage';
            if (window.renderers) renderers.renderParentSelect(artifacts, state.getParentData(), state.getCurrentParentId(), childType);
        } catch (e) { console.error("Parents load error:", e); }
    };

    // ГЛАВНОЕ: вешаем событие на смену проекта
    if (projectSelect) {
        projectSelect.addEventListener('change', function() {
            const selectedId = this.value;
            console.log("Project changed to:", selectedId);
            state.setCurrentProjectId(selectedId); // Сохраняем в state
            if (selectedId) {
                window.loadParents(); // Грузим зависимости
            }
        });
    }

    // Если тип артефакта меняется, тоже перерисовываем список родителей
    if (artifactTypeSelect) {
        artifactTypeSelect.addEventListener('change', () => window.loadParents());
    }
})();
