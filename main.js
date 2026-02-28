// main.js - основной скрипт, инициализация и обработчики событий

(function() {
    const input = document.getElementById("input");
    const sendBtn = document.getElementById("send-btn");
    const messagesDiv = document.getElementById("messages");
    const scrollAnchor = document.getElementById("scroll-anchor");
    const modelSelect = document.getElementById("model-select");
    const modeSelect = document.getElementById("mode-select");
    const statusText = document.getElementById("status-text");
    const projectSelect = document.getElementById("project-select");
    const newProjectBtn = document.getElementById("new-project-btn");
    const deleteProjectBtn = document.getElementById("delete-project-btn");
    const artifactTypeSelect = document.getElementById("artifact-type-select");
    const parentSelect = document.getElementById("parent-select");
    const refreshParentsBtn = document.getElementById("refresh-parents");
    const deleteArtifactBtn = document.getElementById("delete-artifact-btn");
    const saveArtifactBtn = document.getElementById("save-artifact-btn");
    const generateArtifactBtn = document.getElementById("generate-artifact-btn");
    const completeClarificationBtn = document.getElementById("complete-clarification-btn");

    window.loadParents = loadParents;

    marked.setOptions({ gfm: true, breaks: true });

    input.oninput = function () {
        this.style.height = "auto";
        this.style.height = this.scrollHeight + "px";
        document.getElementById("token-count").innerText = `EST_COST: ~${Math.ceil(this.value.length / 4)} TOKENS`;
    };

    // ========== СОХРАНЕНИЕ СОСТОЯНИЯ ==========
    function saveState() {
        if (!state || typeof state.getCurrentProjectId !== 'function') return;
        try {
            const currentState = {
                projectId: state.getCurrentProjectId(),
                model: modelSelect ? modelSelect.value : null,
                mode: modeSelect ? modeSelect.value : null,
                artifactType: artifactTypeSelect ? artifactTypeSelect.value : null,
                parentId: parentSelect ? parentSelect.value : null,
                isSimple: document.getElementById('simple-controls')?.classList.contains('hidden') === false
            };
            localStorage.setItem('mrak_ui_state', JSON.stringify(currentState));
        } catch (e) {
            console.warn('Failed to save state', e);
        }
    }

    function restoreState() {
        const saved = localStorage.getItem('mrak_ui_state');
        if (!saved) return;
        try {
            const st = JSON.parse(saved);
            if (st.projectId) {
                state.setCurrentProjectId(st.projectId);
            }
            if (st.model && modelSelect) modelSelect.value = st.model;
            if (st.mode && modeSelect) modeSelect.value = st.mode;
            if (st.artifactType && artifactTypeSelect) artifactTypeSelect.value = st.artifactType;
            if (st.parentId) {
                state.setCurrentParentId(st.parentId);
            }
            if (st.isSimple && window.simpleMode) {
                window.simpleMode.switchMode('simple');
            } else if (window.simpleMode) {
                window.simpleMode.switchMode('advanced');
            }
        } catch (e) {}
    }

    // ========== ЗАГРУЗКА ДАННЫХ ==========
    async function loadProjects() {
        try {
            const projects = await api.fetchProjects();
            state.setProjects(projects);
            ui.renderProjectSelect(projects, state.getCurrentProjectId());
        } catch (e) {
            ui.showNotification('Ошибка загрузки проектов: ' + e.message, 'error');
        }
    }

    async function loadArtifactTypes() {
        try {
            const types = await api.fetchArtifactTypes();
            state.setArtifactTypes(types);
        } catch (e) {
            console.warn('Failed to load artifact types', e);
        }
    }

    async function loadParents() {
        const pid = state.getCurrentProjectId();
        if (!pid) return;
        try {
            const artifacts = await api.fetchArtifacts(pid);
            state.setArtifacts(artifacts);
            ui.renderParentSelect(artifacts, state.getParentData(), state.getCurrentParentId(), artifactTypeSelect.value);
        } catch (e) {
            ui.showNotification('Ошибка загрузки артефактов: ' + e.message, 'error');
        }
    }

    async function loadModels() {
        try {
            const models = await api.fetchModels();
            state.setModels(models);
            if (modelSelect) {
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
                const saved = localStorage.getItem('mrak_ui_state');
                if (saved) {
                    const st = JSON.parse(saved);
                    if (st.model) modelSelect.value = st.model;
                }
                modelSelect.addEventListener('change', saveState);
            }
        } catch (e) {
            ui.showNotification('Ошибка загрузки моделей: ' + e.message, 'error');
        }
    }

    async function loadModes() {
        try {
            const modes = await api.fetchModes();
            if (modeSelect) {
                modeSelect.innerHTML = '';
                if (modes && modes.length) {
                    modes.forEach(m => {
                        const opt = document.createElement('option');
                        opt.value = m.id;
                        opt.innerText = m.name;
                        if (m.default) opt.selected = true;
                        modeSelect.appendChild(opt);
                    });
                } else {
                    modeSelect.innerHTML = '<option value="01_CORE">01: CORE_SYSTEM</option>';
                }
                const saved = localStorage.getItem('mrak_ui_state');
                if (saved) {
                    const st = JSON.parse(saved);
                    if (st.mode) modeSelect.value = st.mode;
                }
                modeSelect.addEventListener('change', saveState);
            }
        } catch (e) {
            console.error('Ошибка загрузки режимов:', e);
            if (modeSelect) modeSelect.innerHTML = '<option value="01_CORE">01: CORE_SYSTEM</option>';
        }
    }

    async function loadMessages() {
        const pid = state.getCurrentProjectId();
        if (!pid) return;
        try {
            const messages = await api.fetchMessages(pid);
            messagesDiv.innerHTML = '';
            messages.forEach(msg => {
                const userDiv = document.createElement("div");
                userDiv.className = "border-l-2 border-zinc-800 pl-6 text-sm text-zinc-400";
                userDiv.innerText = msg.content.user_input || '...';
                messagesDiv.appendChild(userDiv);

                const assistantDiv = document.createElement("div");
                assistantDiv.className = "markdown-body";
                assistantDiv.innerHTML = marked.parse(msg.content.response || '');
                messagesDiv.appendChild(assistantDiv);
            });
            if (scrollAnchor) scrollAnchor.scrollIntoView({ behavior: "smooth" });
        } catch (e) {
            console.warn('Failed to load messages', e);
        }
    }

    // ========== ОБРАБОТЧИКИ СОБЫТИЙ ==========
    newProjectBtn.onclick = async () => {
        const name = prompt("Введите название проекта:");
        if (!name) return;
        try {
            const data = await api.createProject(name, "");
            await loadProjects();
            projectSelect.value = data.id;
            state.setCurrentProjectId(data.id);
            await loadParents();
            await loadMessages();
            ui.showNotification('Проект создан', 'success');
            saveState();
        } catch (e) {
            ui.showNotification('Ошибка создания проекта: ' + e.message, 'error');
        }
    };

    deleteProjectBtn.onclick = async () => {
        const pid = state.getCurrentProjectId();
        if (!pid) return;
        if (!confirm('Удалить проект? Все артефакты будут безвозвратно удалены.')) return;
        try {
            await api.apiFetch(`/api/projects/${pid}`, { method: 'DELETE' });
            await loadProjects();
            state.setCurrentProjectId('');
            messagesDiv.innerHTML = '';
            ui.showNotification('Проект удалён', 'success');
            saveState();
        } catch (e) {
            ui.showNotification('Ошибка удаления: ' + e.message, 'error');
        }
    };

    refreshParentsBtn.onclick = loadParents;

    projectSelect.addEventListener("change", function() {
        state.setCurrentProjectId(this.value);
        if (artifactTypeSelect) artifactTypeSelect.value = "BusinessIdea";
        if (parentSelect) {
            parentSelect.innerHTML = '<option value="">-- нет --</option>';
        }
        if (generateArtifactBtn) generateArtifactBtn.style.display = 'none';
        if (completeClarificationBtn) completeClarificationBtn.style.display = 'none';
        if (this.value) {
            loadParents();
            loadMessages();
            if (window.simpleMode && document.getElementById('simple-controls')?.classList.contains('hidden') === false) {
                window.simpleMode.updateProgress();
            }
        }
        saveState();
    });

    parentSelect.addEventListener('change', function() {
        const selectedId = this.value;
        state.setCurrentParentId(selectedId);
        ui.updateGenerateButton(state.getParentData(), selectedId, artifactTypeSelect.value);
        saveState();
    });

    artifactTypeSelect.addEventListener('change', function() {
        ui.renderParentSelect(state.getArtifacts(), state.getParentData(), state.getCurrentParentId(), this.value);
        state.setCurrentClarificationSessionId(null);
        if (completeClarificationBtn) completeClarificationBtn.style.display = 'none';
        saveState();
    });

    saveArtifactBtn.onclick = async () => {
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
        const generate = false;
        const model = modelSelect.value;

        try {
            const data = await api.saveArtifact(pid, artifactType, content, parentId, generate, model);
            ui.showNotification(`Артефакт сохранён, ID: ${data.id}`, 'success');
            input.value = "";
            input.style.height = "44px";
            await loadParents();
            if (window.simpleMode && document.getElementById('simple-controls')?.classList.contains('hidden') === false) {
                window.simpleMode.updateProgress();
            }
        } catch (e) {
            ui.showNotification('Ошибка сохранения: ' + e.message, 'error');
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

        try {
            const data = await api.generateArtifact(childType, parentId, feedback, model, pid, null);
            state.setCurrentArtifact({ content: data.result });
            ui.openRequirementsModal(
                childType,
                data.result,
                async (updatedContent, validate) => {
                    try {
                        const saved = await api.saveArtifactPackage(pid, parentId, childType, updatedContent);
                        if (validate) {
                            await api.apiFetch('/api/validate_artifact', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ artifact_id: saved.id, status: 'VALIDATED' })
                            });
                            ui.showNotification('Артефакт подтверждён', 'success');
                        } else {
                            ui.showNotification(`Сохранён пакет, ID: ${saved.id}`, 'success');
                        }
                        ui.closeModal();
                        await loadParents();
                        if (window.simpleMode && document.getElementById('simple-controls')?.classList.contains('hidden') === false) {
                            window.simpleMode.updateProgress();
                        }
                    } catch (e) {
                        ui.showNotification('Ошибка сохранения: ' + e.message, 'error');
                    }
                },
                () => {
                    ui.showNotification('Догенерация пока не реализована', 'info');
                },
                () => { ui.closeModal(); }
            );
        } catch (e) {
            ui.showNotification('Ошибка генерации: ' + e.message, 'error');
        }
    };

    deleteArtifactBtn.onclick = async () => {
        const artifactId = parentSelect.value;
        if (!artifactId) {
            ui.showNotification('Выберите артефакт для удаления', 'error');
            return;
        }
        if (!confirm('Удалить выбранный артефакт?')) return;
        try {
            await api.apiFetch(`/api/artifact/${artifactId}`, { method: 'DELETE' });
            ui.showNotification('Артефакт удалён', 'success');
            await loadParents();
        } catch (e) {
            ui.showNotification('Ошибка удаления: ' + e.message, 'error');
        }
    };

    async function handleClarificationMessage(projectId, artifactType, message, model) {
        let sessionId = state.getCurrentClarificationSessionId();
        if (!sessionId) {
            try {
                const sessions = await api.fetchActiveClarificationSessions(projectId);
                const active = sessions.find(s => s.target_artifact_type === artifactType);
                if (active) {
                    sessionId = active.id;
                    state.setCurrentClarificationSessionId(sessionId);
                }
            } catch (e) {
                console.error('Failed to fetch active sessions', e);
            }
        }

        if (!sessionId) {
            try {
                const data = await api.startClarification(projectId, artifactType, model);
                sessionId = data.id;
                state.setCurrentClarificationSessionId(sessionId);
                if (data.history && data.history.length > 0) {
                    ui.renderClarificationHistory(data.history);
                }
                if (completeClarificationBtn) completeClarificationBtn.style.display = 'inline-block';
            } catch (e) {
                ui.showNotification('Ошибка создания сессии: ' + e.message, 'error');
                return;
            }
        }

        try {
            const data = await api.sendClarificationMessage(sessionId, message);
            ui.renderClarificationHistory(data.history);
            if (completeClarificationBtn) completeClarificationBtn.style.display = 'inline-block';
        } catch (e) {
            ui.showNotification('Ошибка отправки: ' + e.message, 'error');
        }
    }

    completeClarificationBtn.onclick = async () => {
        const sessionId = state.getCurrentClarificationSessionId();
        if (!sessionId) {
            ui.showNotification('Нет активной сессии', 'error');
            return;
        }
        try {
            await api.completeClarificationSession(sessionId);
            ui.showNotification('Сессия завершена', 'success');
            completeClarificationBtn.style.display = 'none';
            state.setCurrentClarificationSessionId(null);
        } catch (e) {
            ui.showNotification('Ошибка завершения: ' + e.message, 'error');
        }
    };

    async function start() {
        const prompt = input.value.trim();
        if (!prompt) return;
        const pid = state.getCurrentProjectId();
        if (!pid) {
            ui.showNotification("Сначала выберите проект", 'error');
            return;
        }
        const mode = modeSelect.value;
        const model = modelSelect.value;

        const isAdvanced = document.getElementById('advanced-controls')?.classList.contains('hidden') === false;
        if (isAdvanced) {
            const artifactType = artifactTypeSelect.value;
            if (state.requiresClarification(artifactType)) {
                await handleClarificationMessage(pid, artifactType, prompt, model);
                return;
            }
        }

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

        messagesDiv.classList.remove('hidden');
        const placeholder = document.getElementById('messages-placeholder');
        if (placeholder) placeholder.style.display = 'none';

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
                if (scrollAnchor) scrollAnchor.scrollIntoView({ behavior: "smooth" });
            }
        } catch (e) {
            assistantDiv.innerHTML = `<span class="text-red-500">SYSTEM_ERROR: ${e.message}</span>`;
        } finally {
            assistantDiv.classList.remove("streaming");
            input.disabled = false; sendBtn.disabled = false;
            statusText.innerText = "SYSTEM_READY";
            input.focus();
            saveState();
            await loadMessages();
        }
    }

    sendBtn.onclick = start;
    input.onkeydown = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); start(); } };

    window.onload = async function() {
        if (state && typeof state.subscribe === 'function') {
            state.subscribe(() => {
                saveState();
            });
        }

        await loadModels();
        await loadModes();
        await loadProjects();
        await loadArtifactTypes(); // ADDED
        restoreState();
        if (state.getCurrentProjectId()) {
            await loadParents();
            await loadMessages();
        }
        if (window.simpleMode) {
            window.simpleMode.init();
        }
    };
})();
