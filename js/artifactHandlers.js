// artifactHandlers.js - работа с артефактами (сохранение, генерация)

(function() {
    const input = document.getElementById("input");
    const parentSelect = document.getElementById("parent-select");
    const artifactTypeSelect = document.getElementById("artifact-type-select");
    const modelSelect = document.getElementById("model-select");
    const generateCheckbox = document.getElementById("generate-checkbox");
    const saveArtifactBtn = document.getElementById("save-artifact-btn");
    const generateArtifactBtn = document.getElementById("generate-artifact-btn");
    const pid = () => state.getCurrentProjectId();

    // Внутренние функции (не глобальные)
    async function handleSave(childType, parentId) {
        if (window.isSaving) return;
        window.isSaving = true;
        let currentContent = state.getCurrentArtifact()?.content;
        if (currentContent === undefined) {
            currentContent = (childType === 'BusinessRequirementPackage' || childType === 'FunctionalRequirementPackage') ? [] : {};
        }
        try {
            const saved = await api.saveArtifactPackage(pid(), parentId, childType, currentContent);
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
            window.isSaving = false;
        }
    }

    async function handleAddMore(childType, parentId) {
        if (window.isSaving) return;
        window.isSaving = true;
        const newFeedback = input.value.trim();
        const existingContent = state.getCurrentArtifact()?.content;
        const model = modelSelect.value;
        try {
            const newData = await api.generateArtifact(childType, parentId, newFeedback, model, pid(), existingContent);
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
                () => handleSave(childType, parentId),
                () => handleAddMore(childType, parentId),
                () => ui.closeModal()
            );
        } catch (e) {
            ui.showNotification('Ошибка генерации: ' + e.message, 'error');
        } finally {
            window.isSaving = false;
        }
    }

    // Сохранение артефакта (кнопка)
    saveArtifactBtn.onclick = async () => {
        if (window.isSaving) return;
        const content = input.value.trim();
        if (!content) {
            ui.showNotification("Введите содержимое артефакта", 'error');
            return;
        }
        if (!pid()) {
            ui.showNotification("Сначала выберите проект", 'error');
            return;
        }
        const artifactType = artifactTypeSelect.value;
        const parentId = parentSelect.value || null;
        const generate = generateCheckbox.checked;
        const model = modelSelect.value;

        window.isSaving = true;
        setLoading(saveArtifactBtn, true);
        try {
            const data = await api.saveArtifact(pid(), artifactType, content, parentId, generate, model);
            ui.showNotification(`Артефакт сохранён, ID: ${data.id}`, 'success');
            input.value = "";
            input.style.height = "44px";
            await window.loadParents();
        } catch (e) {
            ui.showNotification('Ошибка сохранения: ' + e.message, 'error');
        } finally {
            setLoading(saveArtifactBtn, false);
            window.isSaving = false;
        }
    };

    // Генерация/редактирование артефакта (кнопка)
    generateArtifactBtn.onclick = async () => {
        const parentId = parentSelect.value;
        const childType = artifactTypeSelect.value;
        if (!parentId || !childType) return;
        const feedback = input.value.trim();
        const model = modelSelect.value;
        if (!pid()) return;

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
                    const genData = await api.generateArtifact(childType, parentId, feedback, model, pid(), null);
                    contentToShow = genData.result;
                    state.setCurrentArtifact({ content: contentToShow });
                }
            }

            ui.openRequirementsModal(
                childType,
                contentToShow,
                () => handleSave(childType, parentId),
                () => handleAddMore(childType, parentId),
                () => ui.closeModal()
            );
        } catch (e) {
            ui.showNotification('Ошибка: ' + e.message, 'error');
        } finally {
            setLoading(generateArtifactBtn, false);
        }
    };
})();
