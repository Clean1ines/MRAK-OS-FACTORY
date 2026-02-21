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
        } catch (e) {
            ui.showNotification('Ошибка загрузки моделей: ' + e.message, 'error');
        }
    }

    // Новая функция: загрузка режимов промптов
    async function loadModes() {
        try {
            const modes = await api.fetchModes(); // нужно добавить в api.js
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
        } catch (e) {
            ui.showNotification('Ошибка удаления: ' + e.message, 'error');
        }
    };

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
                async () => {
                    const currentContent = state.getCurrentArtifact()?.content;
                    try {
                        const saved = await api.saveArtifactPackage(pid, parentId, childType, currentContent);
                        ui.showNotification(`Сохранён пакет, ID: ${saved.id}`, 'success');
                        ui.closeModal();
                        await loadParents();
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
                // Проверяем, что scrollAnchor существует
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
        }
    }

    sendBtn.onclick = start;
    input.onkeydown = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); start(); } };

    // ========== ИНИЦИАЛИЗАЦИЯ ==========
    window.onload = async function() {
        await loadModels();
        await loadModes();  // Загружаем режимы
        await loadProjects();
        if (state.getCurrentProjectId()) await loadParents();
        // Инициализируем простой режим
        if (window.simpleMode) {
            window.simpleMode.init();
        }
    };
})();
