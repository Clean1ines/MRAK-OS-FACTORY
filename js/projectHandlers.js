// projectHandlers.js - работа с проектами
console.log('[HANDLERS] загрузка начата');

(function() {
    const projectSelect = document.getElementById("project-select");
    const newProjectBtn = document.getElementById("new-project-btn");
    const refreshParentsBtn = document.getElementById("refresh-parents");
    const artifactTypeSelect = document.getElementById("artifact-type-select");
    const generateArtifactBtn = document.getElementById("generate-artifact-btn");
    const parentSelect = document.getElementById("parent-select");

    console.log('[HANDLERS] элементы найдены:', { 
        projectSelect: !!projectSelect, newProjectBtn: !!newProjectBtn, refreshParentsBtn: !!refreshParentsBtn,
        artifactTypeSelect: !!artifactTypeSelect, generateArtifactBtn: !!generateArtifactBtn, parentSelect: !!parentSelect 
    });

    window.loadProjects = async function() {
        console.log('[HANDLERS] loadProjects');
        try {
            const projects = await api.fetchProjects();
            state.setProjects(projects);
            ui.renderProjectSelect(projects, state.getCurrentProjectId());
        } catch (e) {
            console.error('[HANDLERS] loadProjects error:', e);
        }
    };

    window.loadParents = async function() {
        console.log('[HANDLERS] loadParents');
        const pid = state.getCurrentProjectId();
        if (!pid) return;
        try {
            const artifacts = await api.fetchArtifacts(pid);
            state.setArtifacts(artifacts);
            ui.renderParentSelect(artifacts, state.getParentData(), state.getCurrentParentId(), artifactTypeSelect.value);
        } catch (e) {
            console.error('[HANDLERS] loadParents error:', e);
        }
    };

    window.loadModels = async function() {
        console.log('[HANDLERS] loadModels');
        try {
            const models = await api.fetchModels();
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
            }
        } catch (e) {
            console.error('[HANDLERS] loadModels error:', e);
        }
    };

    newProjectBtn.onclick = async () => {
        console.log('[HANDLERS] newProjectBtn click');
        const name = prompt("Введите название проекта:");
        if (!name) return;
        try {
            const data = await api.createProject(name, "");
            await window.loadProjects();
            projectSelect.value = data.id;
            state.setCurrentProjectId(data.id);
            await window.loadParents();
        } catch (e) {
            console.error('[HANDLERS] newProject error:', e);
        }
    };

    projectSelect.addEventListener("change", function(e) {
        console.log('[HANDLERS] projectSelect change', e.target.value);
        state.setCurrentProjectId(e.target.value);
        if (e.target.value) {
            window.loadParents();
        } else {
            parentSelect.innerHTML = '<option value="">-- нет --</option>';
            generateArtifactBtn.style.display = 'none';
        }
    });

    refreshParentsBtn.onclick = window.loadParents;

    console.log('[HANDLERS] загрузка завершена');
})();
