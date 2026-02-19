// projectHandlers.js - работа с проектами

(function() {
    const projectSelect = document.getElementById("project-select");
    const newProjectBtn = document.getElementById("new-project-btn");
    const refreshParentsBtn = document.getElementById("refresh-parents");
    const artifactTypeSelect = document.getElementById("artifact-type-select");
    const generateArtifactBtn = document.getElementById("generate-artifact-btn");
    const parentSelect = document.getElementById("parent-select");

    // Загрузка проектов
    window.loadProjects = async function() {
        try {
            const projects = await api.fetchProjects();
            state.setProjects(projects);
            ui.renderProjectSelect(projects, state.getCurrentProjectId());
        } catch (e) {
            ui.showNotification('Ошибка загрузки проектов: ' + e.message, 'error');
        }
    };

    // Загрузка артефактов (родителей) для текущего проекта
    window.loadParents = async function() {

    window.loadModels = async function() {
        try {
            const models = await api.fetchModels();
            state.setModels(models);
            const modelSelect = document.getElementById("model-select");
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
        } catch (e) {
            ui.showNotification("Ошибка загрузки моделей: " + e.message, "error");
        }
    };

        const pid = state.getCurrentProjectId();
        if (!pid) return;
        setLoading(refreshParentsBtn, true);
        try {
            const artifacts = await api.fetchArtifacts(pid);
            state.setArtifacts(artifacts);
            ui.renderParentSelect(artifacts, state.getParentData(), state.getCurrentParentId(), artifactTypeSelect.value);
        } catch (e) {
            ui.showNotification('Ошибка загрузки артефактов: ' + e.message, 'error');
        } finally {
            setLoading(refreshParentsBtn, false);
        }
    };

    // Создание проекта
    newProjectBtn.onclick = async () => {
        const name = prompt("Введите название проекта:");
        if (!name) return;
        setLoading(newProjectBtn, true);
        try {
            const data = await api.createProject(name, "");
            await window.loadProjects();
            projectSelect.value = data.id;
            state.setCurrentProjectId(data.id);
            await window.loadParents();

    window.loadModels = async function() {
        try {
            const models = await api.fetchModels();
            state.setModels(models);
            const modelSelect = document.getElementById("model-select");
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
        } catch (e) {
            ui.showNotification("Ошибка загрузки моделей: " + e.message, "error");
        }
    };

            ui.showNotification('Проект создан', 'success');
        } catch (e) {
            ui.showNotification('Ошибка создания проекта: ' + e.message, 'error');
        } finally {
            setLoading(newProjectBtn, false);
        }
    };

    // Переключение проекта
    projectSelect.addEventListener("change", function() {
        state.setCurrentProjectId(this.value);
        if (this.value) {
            window.loadParents();

    window.loadModels = async function() {
        try {
            const models = await api.fetchModels();
            state.setModels(models);
            const modelSelect = document.getElementById("model-select");
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
        } catch (e) {
            ui.showNotification("Ошибка загрузки моделей: " + e.message, "error");
        }
    };

        } else {
            parentSelect.innerHTML = '<option value="">-- нет --</option>';
            generateArtifactBtn.style.display = 'none';
        }
    });

    // Кнопка обновления списка родителей
    refreshParentsBtn.onclick = window.loadParents;

    window.loadModels = async function() {
        try {
            const models = await api.fetchModels();
            state.setModels(models);
            const modelSelect = document.getElementById("model-select");
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
        } catch (e) {
            ui.showNotification("Ошибка загрузки моделей: " + e.message, "error");
        }
    };

})();
