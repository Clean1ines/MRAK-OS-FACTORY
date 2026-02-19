(function() {
    const modelSelect = document.getElementById("model-select");
    const projectSelect = document.getElementById("project-select");

    window.loadModels = async function() {
        if (!modelSelect) return;
        const models = await api.fetchModels();
        
        modelSelect.innerHTML = "";
        
        if (models.length === 0) {
            modelSelect.innerHTML = '<option value="llama-3.3-70b-versatile">llama-3.3-70b-versatile (API EMPTY)</option>';
            return;
        }

        models.forEach(m => {
            const opt = document.createElement("option");
            // Пробуем все варианты ключей из доки: id, model, или просто строка
            const val = m.id || m.model || (typeof m === 'string' ? m : null);
            if (val) {
                opt.value = val;
                opt.innerText = val;
                // Автовыбор мощной модели из твоей доки
                if (val === "openai/gpt-oss-120b" || val === "llama-3.3-70b-versatile") {
                    opt.selected = true;
                }
                modelSelect.appendChild(opt);
            }
        });
    };

    window.loadProjects = async function() {
        try {
            const projects = await api.fetchProjects();
            state.setProjects(projects);
            if (window.renderers) renderers.renderProjectSelect(projects, state.getCurrentProjectId());
        } catch (e) { console.error(e); }
    };

    if (projectSelect) {
        projectSelect.onchange = function() {
            const pid = this.value;
            state.setCurrentProjectId(pid);
            console.log("Project selected:", pid);
            if (window.loadParents) window.loadParents();
        };
    }
})();
