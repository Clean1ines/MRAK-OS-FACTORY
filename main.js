(function() {
    const input = document.getElementById("input");
    const sendBtn = document.getElementById("send-btn");
    const messagesDiv = document.getElementById("messages");
    const scrollAnchor = document.getElementById("scroll-anchor");
    const modelSelect = document.getElementById("model-select");
    const statusText = document.getElementById("status-text");
    const projectSelect = document.getElementById("project-select");
    const newProjectBtn = document.getElementById("new-project-btn");
    const deleteProjectBtn = document.getElementById("delete-project-btn");
    const artifactTypeSelect = document.getElementById("artifact-type-select");
    const parentSelect = document.getElementById("parent-select");
    const refreshParentsBtn = document.getElementById("refresh-parents");
    const deleteArtifactBtn = document.getElementById("delete-artifact-btn");
    const generateCheckbox = document.getElementById("generate-checkbox");
    const saveArtifactBtn = document.getElementById("save-artifact-btn");
    const generateArtifactBtn = document.getElementById("generate-artifact-btn");

    let isSaving = false;

    marked.setOptions({ gfm: true, breaks: true });

    input.oninput = function () {
        this.style.height = "auto";
        this.style.height = this.scrollHeight + "px";
        document.getElementById("token-count").innerText = `EST_COST: ~${Math.ceil(this.value.length / 4)} TOKENS`;
    };

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

    async function loadProjects() {
        try {
            const projects = await api.fetchProjects();
            state.setProjects(projects);
            ui.renderProjectSelect(projects, state.getCurrentProjectId());
        } catch (e) {
            ui.showNotification('Ошибка загрузки проектов: ' + e.message, 'error');
        }
    }

    newProjectBtn.onclick = async () => {
        const name = prompt("Введите название проекта:");
        if (!name) return;
        setLoading(newProjectBtn, true);
        try {
            const data = await api.createProject(name, "");
            await loadProjects();
            projectSelect.value = data.id;
            state.setCurrentProjectId(data.id);
            await loadParents();
            ui.showNotification('Проект создан', 'success');
        } catch (e) {
            ui.showNotification('Ошибка создания проекта: ' + e.message, 'error');
        } finally {
            setLoading(newProjectBtn, false);
        }
    };

    async function loadParents() {
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
    }

    refreshParentsBtn.onclick = loadParents;

    projectSelect.addEventListener("change", function() {
        state.setCurrentProjectId(this.value);
        if (this.value) {
            loadParents();
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
        loadParents();
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
            await loadParents();
        } catch (e) {
            ui.showNotification('Ошибка сохранения: ' + e.message, 'error');
        } finally {
            setLoading(saveArtifactBtn, false);
            isSaving = false;
        }
    };

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
                    await loadParents();
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

    deleteProjectBtn.onclick = async () => {
        const pid = state.getCurrentProjectId();
        if (!pid) {
            ui.showNotification("Нет выбранного проекта", "error");
            return;
        }
        if (!confirm("Вы уверены, что хотите удалить проект и все его артефакты? Это действие необратимо.")) return;
        try {
            const res = await fetch(`/api/projects/${pid}`, { method: "DELETE" });
            if (res.ok) {
                ui.showNotification("Проект удалён", "success");
                state.setCurrentProjectId("");
                await loadProjects();
                parentSelect.innerHTML = '<option value="">-- нет --</option>';
                generateArtifactBtn.style.display = "none";
            } else {
                let errorText = "Ошибка удаления";
                const contentType = res.headers.get("content-type");
                if (contentType && contentType.includes("application/json")) {
                    const err = await res.json();
                    errorText = err.error || errorText;
                } else {
                    errorText = await res.text();
                }
                ui.showNotification(errorText, "error");
            }
        } catch (e) {
            ui.showNotification("Ошибка сети: " + e.message, "error");
        }
    };

    deleteArtifactBtn.onclick = async () => {
        const aid = parentSelect.value;
        if (!aid) {
            ui.showNotification("Нет выбранного артефакта", "error");
            return;
        }
        if (!confirm("Удалить выбранный артефакт? Дочерние артефакты останутся, но потеряют связь.")) return;
        try {
            const res = await fetch(`/api/artifacts/${aid}`, { method: "DELETE" });
            if (res.ok) {
                ui.showNotification("Артефакт удалён", "success");
                await loadParents();
            } else {
                let errorText = "Ошибка удаления";
                const contentType = res.headers.get("content-type");
                if (contentType && contentType.includes("application/json")) {
                    const err = await res.json();
                    errorText = err.error || errorText;
                } else {
                    errorText = await res.text();
                }
                ui.showNotification(errorText, "error");
            }
        } catch (e) {
            ui.showNotification("Ошибка сети: " + e.message, "error");
        }
    };

    async function loadModels() {
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
    }

    window.onload = async function() {
        await loadModels();
        await loadProjects();
        if (state.getCurrentProjectId()) await loadParents();
    };

    sendBtn.onclick = start;
    input.onkeydown = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); start(); } };

    async function start() {
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
        const toolbar = createMessageToolbar(assistantDiv);
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
    }

    function createMessageToolbar(messageElement) {
        const toolbar = document.createElement("div");
        toolbar.className = "message-toolbar";
        const copyBtn = document.createElement("button");
        copyBtn.innerText = "Copy";
        copyBtn.onclick = async () => {
            try { await navigator.clipboard.writeText(messageElement.innerText); } catch (_) {
                const textarea = document.createElement("textarea");
                textarea.value = messageElement.innerText;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand("copy");
                document.body.removeChild(textarea);
            }
        };
        const editBtn = document.createElement("button");
        editBtn.innerText = "Edit";
        editBtn.onclick = () => {
            const raw = messageElement.dataset.rawMarkdown || messageElement.innerText;
            const editArea = document.createElement("textarea");
            editArea.value = raw;
            editArea.className = "w-full bg-transparent text-gray-200 p-2 border border-zinc-700 rounded";
            const saveBtn = document.createElement("button");
            saveBtn.innerText = "Save";
            saveBtn.className = "ml-2 p-1 bg-emerald-600/20 rounded";
            saveBtn.onclick = () => {
                const newRaw = editArea.value;
                messageElement.innerHTML = marked.parse(newRaw);
                messageElement.dataset.rawMarkdown = newRaw;
                editArea.remove();
                saveBtn.remove();
            };
            messageElement.appendChild(editArea);
            messageElement.appendChild(saveBtn);
        };
        const regenerateBtn = document.createElement("button");
        regenerateBtn.innerText = "Regenerate";
        regenerateBtn.onclick = async () => {
            const original = messageElement.dataset.originalPrompt;
            if (!original) return;
            input.value = original;
            input.style.height = "auto";
            await start();
        };
        const shareBtn = document.createElement("button");
        shareBtn.innerText = "Share";
        shareBtn.onclick = async () => {
            const shareText = `Shared Message:\n${messageElement.innerText}`;
            try { await navigator.clipboard.writeText(shareText); } catch (_) {
                const textarea = document.createElement("textarea");
                textarea.value = shareText;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand("copy");
                document.body.removeChild(textarea);
            }
        };
        toolbar.appendChild(copyBtn);
        toolbar.appendChild(editBtn);
        toolbar.appendChild(regenerateBtn);
        toolbar.appendChild(shareBtn);
        return toolbar;
    }
})();
