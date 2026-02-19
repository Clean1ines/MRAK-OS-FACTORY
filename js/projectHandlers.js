// projectHandlers.js - работа с проектами

(function() {
    const projectSelect = document.getElementById("project-select");
    const newProjectBtn = document.getElementById("new-project-btn");
    const refreshParentsBtn = document.getElementById("refresh-parents");
    const artifactTypeSelect = document.getElementById("artifact-type-select");
    const generateArtifactBtn = document.getElementById("generate-artifact-btn");
    const parentSelect = document.getElementById("parent-select");

    window.loadProjects = async function() {
        try {
            const projects = await api.fetchProjects();
            state.setProjects(projects);
            ui.renderProjectSelect(projects, state.getCurrentProjectId());
        } catch (e) {
            console.error(e);
        }
    };

    window.loadParents = async function() {
        const pid = state.getCurrentProjectId();
        if (!pid) return;
        try {
            const artifacts = await api.fetchArtifacts(pid);
            state.setArtifacts(artifacts);
            ui.renderParentSelect(artifacts, state.getParentData(), state.getCurrentParentId(), artifactTypeSelect.value);
        } catch (e) {
            console.error(e);
        }
    };

    window.loadModels = async function() {
        try {
            const models = await api.fetchModels();
            state.setModels(models);
        } catch (e) {
            console.error(e);
        }
    };

    newProjectBtn.onclick = async () => {
        const name = prompt("Введите название проекта:");
        if (!name) return;
        try {
            const data = await api.createProject(name, "");
            await window.loadProjects();
            projectSelect.value = data.id;
            state.setCurrentProjectId(data.id);
            await window.loadParents();
        } catch (e) {
            console.error(e);
        }
    };

    projectSelect.addEventListener("change", function() {
        state.setCurrentProjectId(this.value);
        if (this.value) {
            window.loadParents();
        } else {
            parentSelect.innerHTML = '<option value="">-- нет --</option>';
            generateArtifactBtn.style.display = 'none';
        }
    });

    refreshParentsBtn.onclick = window.loadParents;
})();
