// handlers.js - все обработчики событий

(function() {
    // Импортируем глобальные объекты (предполагается, что api, state, ui уже загружены)
    const input = document.getElementById("input");
    const sendBtn = document.getElementById("send-btn");
    const messagesDiv = document.getElementById("messages");
    const scrollAnchor = document.getElementById("scroll-anchor");
    const modelSelect = document.getElementById("model-select");
    const statusText = document.getElementById("status-text");
    const projectSelect = document.getElementById("project-select");
    const newProjectBtn = document.getElementById("new-project-btn");
    const artifactTypeSelect = document.getElementById("artifact-type-select");
    const parentSelect = document.getElementById("parent-select");
    const refreshParentsBtn = document.getElementById("refresh-parents");
    const generateCheckbox = document.getElementById("generate-checkbox");
    const saveArtifactBtn = document.getElementById("save-artifact-btn");
    const generateArtifactBtn = document.getElementById("generate-artifact-btn");

    // Флаг для блокировки повторных сохранений
    let isSaving = false;

    // Вспомогательная функция загрузки (будет определена в main.js, но здесь используем window)
    function setLoading(button, isLoading) {
        if (!button) return;
        if (isLoading) {
            button.disabled = true;
            button.dataset.originalText = button.innerText;
            button.innerHTML = '<span class="spinner"></span> Загрузка...';
        } else {
            button.disabled = false;
            button.innerText = button.dataset.originalText || button.innerText;
        }
    }

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
            ui.showNotification('Проект создан', 'success');
        } catch (e) {
            ui.showNotification('Ошибка создания проекта: ' + e.message, 'error');
        } finally {
            setLoading(newProjectBtn, false);
        }
    };

    // Загрузка родителей (артефактов) для текущего проекта
    window.loadParents = async function() {
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

    refreshParentsBtn.onclick = window.loadParents;

    projectSelect.addEventListener("change", function() {
        state.setCurrentProjectId(this.value);
        if (this.value) {
            window.loadParents();
        } else {
            parentSelect.innerHTML = '<option value="">-- нет --</option>';
            generateArtifactBtn.style.display = 'none';
        }
    });

    parentSelect.addEventListener('change', function() {
        const selectedId = this.value;
        state.setCurrentParentId(selectedId);
        ui.updateGenerateButton(state.getParentData(), selectedId, artifactTypeSelect.value);
    });

    artifactTypeSelect.addEventListener('change', function() {
        const selectedParentId = parentSelect.value;
        if (selectedParentId) {
            ui.updateGenerateButton(state.getParentData(), selectedParentId, artifactTypeSelect.value);
        }
        // При смене типа нужно перерисовать список родителей с учётом нового типа
        window.loadParents();
    });

    saveArtifactBtn.onclick = async () => {
        if (isSaving) return;
        const content = input.value.trim();
        if (!content) {
            ui.showNotification("Введите содержимое артефакта", 'error');
            return;
        }
        const pid = state.getCurrentProjectId();
        if (!pid) {
            ui.showNotification("Сначала выберите проект", 'error');
            return;
        }
        const artifactType = artifactTypeSelect.value;
        const parentId = parentSelect.value || null;
        const generate = generateCheckbox.checked;
        const model = modelSelect.value;

        isSaving = true;
        setLoading(saveArtifactBtn, true);
        try {
            const data = await api.saveArtifact(pid, artifactType, content, parentId, generate, model);
            ui.showNotification(`Артефакт сохранён, ID: ${data.id}`, 'success');
            input.value = "";
            input.style.height = "44px";
            await window.loadParents();
        } catch (e) {
            ui.showNotification('Ошибка сохранения: ' + e.message, 'error');
        } finally {
            setLoading(saveArtifactBtn, false);
            isSaving = false;
        }
    };

    // Универсальный обработчик генерации/редактирования
    generateArtifactBtn.onclick = async () => {
        const parentId = parentSelect.value;
        const childType = artifactTypeSelect.value;
        if (!parentId || !childType) return;
        const feedback = input.value.trim();
        const model = modelSelect.value;
        const pid = state.getCurrentProjectId();
        if (!pid) return;

        setLoading(generateArtifactBtn, true);
        try {
            // Проверяем кеш
            let cached = state.getArtifactCache(parentId, childType);
            let contentToShow;

            if (cached && cached.content) {
                contentToShow = cached.content;
                state.setCurrentArtifact(cached);
            } else {
                const data = await api.fetchLatestArtifact(parentId, childType);
                if (data.exists) {
                    state.setArtifactCache(parentId, childType, {
                        id: data.artifact_id,
                        content: data.content
                    });
                    contentToShow = data.content;
                    state.setCurrentArtifact({
                        id: data.artifact_id,
                        content: data.content
                    });
                } else {
                    const genData = await api.generateArtifact(childType, parentId, feedback, model, pid, null);
                    contentToShow = genData.result;
                    state.setCurrentArtifact({ content: contentToShow });
                }
            }

            const handleSave = async () => {
                if (isSaving) return;
                isSaving = true;
                let currentContent = state.getCurrentArtifact()?.content;
                if (currentContent === undefined) {
                    currentContent = (childType === 'BusinessRequirementPackage' || childType === 'FunctionalRequirementPackage') ? [] : {};
                }
                try {
                    const saved = await api.saveArtifactPackage(pid, parentId, childType, currentContent);
                    if (saved.duplicate) {
                        ui.showNotification(`Пакет не изменился, ID: ${saved.id}`, 'info');
                    } else {
                        ui.showNotification(`Сохранён пакет, ID: ${saved.id}`, 'success');
                    }
                    state.setArtifactCache(parentId, childType, {
                        id: saved.id,
                        content: currentContent
                    });
                    ui.closeModal();
                    await window.loadParents();
                } catch (e) {
                    ui.showNotification('Ошибка сохранения: ' + e.message, 'error');
                } finally {
                    isSaving = false;
                }
            };

            const handleAddMore = async () => {
                if (isSaving) return;
                isSaving = true;
                const newFeedback = input.value.trim();
                const existingContent = state.getCurrentArtifact()?.content;
                try {
                    const newData = await api.generateArtifact(childType, parentId, newFeedback, model, pid, existingContent);
                    const newContent = newData.result;
                    let combined;
                    if (childType === 'BusinessRequirementPackage' || childType === 'FunctionalRequirementPackage') {
                        const currentArray = Array.isArray(existingContent) ? existingContent : [];
                        const newArray = Array.isArray(newContent) ? newContent : [];
                        combined = currentArray.concat(newArray);
                    } else {
                        combined = newContent;
                    }
                    state.setCurrentArtifact({ content: combined });
                    ui.openRequirementsModal(
                        childType,
                        combined,
                        handleSave,
                        handleAddMore,
                        () => { ui.closeModal(); }
                    );
                } catch (e) {
                    ui.showNotification('Ошибка генерации: ' + e.message, 'error');
                } finally {
                    isSaving = false;
                }
            };

            ui.openRequirementsModal(
                childType,
                contentToShow,
                handleSave,
                handleAddMore,
                () => { ui.closeModal(); }
            );
        } catch (e) {
            ui.showNotification('Ошибка: ' + e.message, 'error');
        } finally {
            setLoading(generateArtifactBtn, false);
        }
    };

    // Загрузка моделей
    window.loadModels = async function() {
        try {
            const models = await api.fetchModels();
            state.setModels(models);
            modelSelect.innerHTML = '';
            models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.id;
                opt.innerText = m.id.toUpperCase();
                if (m.id === "openai/gpt-oss-120b" || m.id === "llama-3.3-70b-versatile") {
                    opt.selected = true;
                }
                modelSelect.appendChild(opt);
            });
        } catch (e) {
            ui.showNotification('Ошибка загрузки моделей: ' + e.message, 'error');
        }
    };

    // Отправка сообщения (чат)
    window.start = async function() {
        const prompt = input.value.trim();
        if (!prompt) return;
        const pid = state.getCurrentProjectId();
        if (!pid) {
            ui.showNotification("Сначала выберите проект", 'error');
            return;
        }
        const mode = document.getElementById("mode-select").value;
        const model = modelSelect.value;

        input.value = ""; input.style.height = "44px";
        input.disabled = true; sendBtn.disabled = true;
        statusText.innerText = "NEURAL_LINK_ESTABLISHED...";

        const userDiv = document.createElement("div");
        userDiv.className = "border-l-2 border-zinc-800 pl-6 text-sm text-zinc-400";
        userDiv.innerText = prompt;
        messagesDiv.appendChild(userDiv);

        const assistantDiv = document.createElement("div");
        assistantDiv.className = "markdown-body streaming";
        messagesDiv.appendChild(assistantDiv);
        assistantDiv.dataset.originalPrompt = prompt;
        const toolbar = window.createMessageToolbar(assistantDiv);
        messagesDiv.appendChild(toolbar);

        try {
            const res = await fetch("/api/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ prompt, mode, model, project_id: pid })
            });
            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let raw = "";
            let metaDone = false;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                let chunk = decoder.decode(value);
                if (!metaDone && chunk.includes("__METADATA__")) {
                    const parts = chunk.split("__");
                    const meta = parts[2].split("|");
                    document.getElementById("q-tokens").innerText = meta[0];
                    document.getElementById("q-req").innerText = meta[1];
                    chunk = parts.slice(3).join("__");
                    metaDone = true;
                }
                raw += chunk;
                assistantDiv.innerHTML = marked.parse(raw);
                assistantDiv.dataset.rawMarkdown = raw;
                scrollAnchor.scrollIntoView({ behavior: "smooth" });
            }
        } catch (e) {
            assistantDiv.innerHTML = `<span class="text-red-500">SYSTEM_ERROR: ${e.message}</span>`;
        } finally {
            assistantDiv.classList.remove("streaming");
            input.disabled = false; sendBtn.disabled = false;
            statusText.innerText = "SYSTEM_READY";
            input.focus();
        }
    };

    sendBtn.onclick = window.start;
    input.onkeydown = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); window.start(); } };
})();
