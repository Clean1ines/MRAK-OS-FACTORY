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

    // Экспортируем функцию loadParents для использования в simpleMode.js
    window.loadParents = loadParents;

    marked.setOptions({ gfm: true, breaks: true });

    input.oninput = function () {
        this.style.height = "auto";
        this.style.height = this.scrollHeight + "px";
        document.getElementById("token-count").innerText = `EST_COST: ~${Math.ceil(this.value.length / 4)} TOKENS`;
    };

    // ========== СОХРАНЕНИЕ СОСТОЯНИЯ ==========
    function saveState() {
        const state = {
            projectId: state.getCurrentProjectId(),
            model: modelSelect.value,
            mode: modeSelect.value,
            artifactType: artifactTypeSelect.value,
            parentId: parentSelect.value,
            isSimple: document.getElementById('simple-controls')?.classList.contains('hidden') === false
        };
        localStorage.setItem('mrak_ui_state', JSON.stringify(state));
    }

    function restoreState() {
        const saved = localStorage.getItem('mrak_ui_state');
        if (!saved) return;
        try {
            const st = JSON.parse(saved);
            if (st.projectId) {
                state.setCurrentProjectId(st.projectId);
                // проект загрузится позже, восстановим остальное после загрузки
            }
            if (st.model) modelSelect.value = st.model;
            if (st.mode) modeSelect.value = st.mode;
            if (st.artifactType) artifactTypeSelect.value = st.artifactType;
            if (st.parentId) {
                // родитель будет восстановлен после загрузки артефактов
                state.setCurrentParentId(st.parentId);
            }
            if (st.isSimple) {
                window.simpleMode?.switchMode('simple');
            } else {
                window.simpleMode?.switchMode('advanced');
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

    async function loadParents() {
        const pid = state.getCurrentProjectId();
        if (!pid) return;
        try {
            const artifacts = await api.fetchArtifacts(pid);
            state.setArtifacts(artifacts);
            // Передаём текущий тип артефакта для фильтрации
            ui.renderParentSelect(artifacts, state.getParentData(), state.getCurrentParentId(), artifactTypeSelect.value);
        } catch (e) {
            ui.showNotification('Ошибка загрузки артефактов: ' + e.message, 'error');
        }
    }

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
            // Восстанавливаем сохранённую модель
            const saved = localStorage.getItem('mrak_ui_state');
            if (saved) {
                const st = JSON.parse(saved);
                if (st.model) modelSelect.value = st.model;
            }
            modelSelect.addEventListener('change', saveState);
        } catch (e) {
            ui.showNotification('Ошибка загрузки моделей: ' + e.message, 'error');
        }
    }

    async function loadModes() {
        try {
            const modes = await api.fetchModes();
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
            // Восстанавливаем сохранённый режим
            const saved = localStorage.getItem('mrak_ui_state');
            if (saved) {
                const st = JSON.parse(saved);
                if (st.mode) modeSelect.value = st.mode;
            }
            modeSelect.addEventListener('change', saveState);
        } catch (e) {
            console.error('Ошибка загрузки режимов:', e);
            modeSelect.innerHTML = '<option value="01_CORE">01: CORE_SYSTEM</option>';
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
            await apiFetch(`/api/projects/${pid}`, { method: 'DELETE' });
            await loadProjects();
            state.setCurrentProjectId('');
            ui.showNotification('Проект удалён', 'success');
            saveState();
        } catch (e) {
            ui.showNotification('Ошибка удаления: ' + e.message, 'error');
        }
    };

    refreshParentsBtn.onclick = loadParents;

    projectSelect.addEventListener("change", function() {
        state.setCurrentProjectId(this.value);
        // Сбрасываем выбранный родитель и тип при смене проекта
        artifactTypeSelect.value = "BusinessIdea"; // или первое значение
        parentSelect.innerHTML = '<option value="">-- нет --</option>';
        generateArtifactBtn.style.display = 'none';
        if (this.value) {
            loadParents();
            // Обновляем прогресс в простом режиме
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
        // Мгновенно перерисовываем родительский селектор с фильтрацией по новому типу
        ui.renderParentSelect(state.getArtifacts(), state.getParentData(), state.getCurrentParentId(), this.value);
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
        const generate = false; // Сохраняем как есть, без генерации
        const model = modelSelect.value;

        try {
            const data = await api.saveArtifact(pid, artifactType, content, parentId, generate, model);
            ui.showNotification(`Артефакт сохранён, ID: ${data.id}`, 'success');
            input.value = "";
            input.style.height = "44px";
            await loadParents();
            // Обновляем прогресс в простом режиме
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
            // Открываем модальное окно для редактирования/сохранения
            ui.openRequirementsModal(
                childType,
                data.result,
                async (updatedContent, validate) => {
                    // Сохраняем изменения (validate = true если нажата кнопка "Подтвердить")
                    try {
                        const saved = await api.saveArtifactPackage(pid, parentId, childType, updatedContent);
                        if (validate) {
                            await apiFetch('/api/validate_artifact', {
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
                        // Обновляем прогресс в простом режиме
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
            await apiFetch(`/api/artifact/${artifactId}`, { method: 'DELETE' });
            ui.showNotification('Артефакт удалён', 'success');
            await loadParents();
        } catch (e) {
            ui.showNotification('Ошибка удаления: ' + e.message, 'error');
        }
    };

    // ========== ЧАТ-ФУНКЦИЯ (отправка сообщения) ==========
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

        // Показываем messagesDiv, если он был скрыт
        messagesDiv.classList.remove('hidden');

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
                if (scrollAnchor) {
                    scrollAnchor.scrollIntoView({ behavior: "smooth" });
                }
            }
        } catch (e) {
            assistantDiv.innerHTML = `<span class="text-red-500">SYSTEM_ERROR: ${e.message}</span>`;
        } finally {
            assistantDiv.classList.remove("streaming");
            input.disabled = false; sendBtn.disabled = false;
            statusText.innerText = "SYSTEM_READY";
            input.focus();
            saveState();
        }
    }

    sendBtn.onclick = start;
    input.onkeydown = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); start(); } };

    // ========== ИНИЦИАЛИЗАЦИЯ ==========
    window.onload = async function() {
        await loadModels();
        await loadModes();
        await loadProjects();
        restoreState();
        if (state.getCurrentProjectId()) await loadParents();
        // Инициализируем простой режим
        if (window.simpleMode) {
            window.simpleMode.init();
        }
        // Подписываемся на изменения состояния для сохранения
        state.subscribe(() => {
            saveState();
        });
    };
})();