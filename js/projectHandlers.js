(function() {
    const modelSelect = document.getElementById("model-select");

    window.loadModels = async function() {
        if (!modelSelect) return;
        
        // СРАЗУ втыкаем дефолты, не дожидаясь ответа API
        modelSelect.innerHTML = `
            <option value="llama-3.3-70b-versatile">LLAMA-3.3-70B-VERSATILE</option>
            <option value="llama3-70b-8192">LLAMA3-70B-8192</option>
            <option value="mixtral-8x7b-32768">MIXTRAL-8X7B-32768</option>
        `;

        try {
            const models = await api.fetchModels();
            if (models && models.length > 0) {
                state.setModels(models);
                modelSelect.innerHTML = ""; // Очищаем дефолты и ставим актуальное
                models.forEach(m => {
                    const id = (typeof m === 'object') ? (m.id || m.name) : m;
                    const opt = document.createElement("option");
                    opt.value = id;
                    opt.innerText = id.toUpperCase();
                    if (id.includes("70b")) opt.selected = true;
                    modelSelect.appendChild(opt);
                });
            }
        } catch (e) {
            console.log("Working with hardcoded fallbacks");
        }
    };

    window.loadProjects = async function() {
        try {
            const projects = await api.fetchProjects();
            state.setProjects(projects);
            if (window.ui && ui.renderProjectSelect) ui.renderProjectSelect(projects, state.getCurrentProjectId());
        } catch (e) { console.error(e); }
    };
})();
