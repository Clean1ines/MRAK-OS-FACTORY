// projectHandlers.js - работа с проектами и загрузка моделей

(function() {
    console.log('[HANDLERS] module start');

    const projectSelect = document.getElementById("project-select");
    const newProjectBtn = document.getElementById("new-project-btn");
    const refreshParentsBtn = document.getElementById("refresh-parents");
    const artifactTypeSelect = document.getElementById("artifact-type-select");
    const generateArtifactBtn = document.getElementById("generate-artifact-btn");
    const parentSelect = document.getElementById("parent-select");

    console.log('[HANDLERS] elements found:', { 
        projectSelect: !!projectSelect, 
        newProjectBtn: !!newProjectBtn,
        refreshParentsBtn: !!refreshParentsBtn,
        artifactTypeSelect: !!artifactTypeSelect,
        generateArtifactBtn: !!generateArtifactBtn,
        parentSelect: !!parentSelect 
    });

    window.loadProjects = async function() {
        console.log('[HANDLERS] loadProjects called');
        try {
            const projects = await api.fetchProjects();
            console.log('[HANDLERS] projects fetched:', projects.length);
            state.setProjects(projects);
            ui.renderProjectSelect(projects, state.getCurrentProjectId());
        } catch (e) {
            console.error('[HANDLERS] loadProjects error:', e);
        }
    };

    window.loadParents = async function() {
        console.log('[HANDLERS] loadParents called');
        const pid = state.getCurrentProjectId();
        console.log('[HANDLERS] currentProjectId from state:', pid);
        if (!pid) {
            console.log('[HANDLERS] no pid, exiting');
            return;
        }
        try {
            const artifacts = await api.fetchArtifacts(pid);
            console.log('[HANDLERS] artifacts fetched:', artifacts.length);
            state.setArtifacts(artifacts);
            console.log('[HANDLERS] about to call ui.renderParentSelect');
            ui.renderParentSelect(artifacts, state.getParentData(), state.getCurrentParentId(), artifactTypeSelect.value);
            console.log('[HANDLERS] renderParentSelect called');
        } catch (e) {
            console.error('[HANDLERS] loadParents error:', e);
        }
    };

    window.loadModels = async function() {
        console.log('[HANDLERS] loadModels called');
        try {
            const models = await api.fetchModels();
            console.log('[HANDLERS] models fetched:', models.length);
            state.setModels(models);
            const modelSelect = document.getElementById("model-select");
            if (modelSelect) {
                modelSelect.innerHTML = "";
                models.forEach(m => {
                    const opt = document.createElement("option");
                    opt.value = m.id;
                    opt.innerText = m.id.toUpperCase();
                    if (m.id === "openai/gpt-oss-120b" || m.id === "llama-3.3-70b-versatile") {
                        opt.selected = true;
                    }
                    modelSelect.appendChild(opt);
                });
                console.log('[HANDLERS] modelSelect populated');
            }
        } catch (e) {
            console.error('[HANDLERS] loadModels error:', e);
        }
    };

    newProjectBtn.onclick = async () => {
        console.log('[HANDLERS] newProjectBtn clicked');
        const name = prompt("Введите название проекта:");
        if (!name) return;
        try {
            const data = await api.createProject(name, "");
            console.log('[HANDLERS] project created:', data);
            await window.loadProjects();
            projectSelect.value = data.id;
            state.setCurrentProjectId(data.id);
            await window.loadParents();
        } catch (e) {
            console.error('[HANDLERS] newProject error:', e);
        }
    };

    projectSelect.addEventListener("change", function(e) {
        console.log('[HANDLERS] projectSelect change to', e.target.value);
        state.setCurrentProjectId(e.target.value);
        if (e.target.value) {
            window.loadParents();
        } else {
            parentSelect.innerHTML = '<option value="">-- нет --</option>';
            generateArtifactBtn.style.display = 'none';
        }
    });

    refreshParentsBtn.onclick = window.loadParents;

    console.log('[HANDLERS] module loaded');
})();
