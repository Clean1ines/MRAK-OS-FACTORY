(function() {
    const input = document.getElementById("input");
    const parentSelect = document.getElementById("parent-select");
    const artifactTypeSelect = document.getElementById("artifact-type-select");
    const modelSelect = document.getElementById("model-select");
    const saveArtifactBtn = document.getElementById("save-artifact-btn");
    const generateArtifactBtn = document.getElementById("generate-artifact-btn");
    const pid = () => state.getCurrentProjectId();

    artifactTypeSelect.onchange = async () => {
        if (window.loadParents) await window.loadParents();
    };

    parentSelect.onchange = () => {
        if (window.renderers) renderers.updateGenerateButton(state.getParentData(), parentSelect.value, artifactTypeSelect.value);
    };

    async function handleSave(childType, parentId) {
        if (window.isSaving) return;
        window.isSaving = true;
        let content = state.getCurrentArtifact()?.content || (childType.includes('Package') ? [] : {});
        try {
            const saved = await api.saveArtifactPackage(pid(), parentId, childType, content);
            ui.showNotification(`Сохранён: ${saved.id}`, 'success');
            ui.closeModal();
            if (window.loadParents) await window.loadParents();
        } catch (e) {
            ui.showNotification('Ошибка: ' + e.message, 'error');
        } finally {
            window.isSaving = false;
        }
    }

    async function handleAddMore(childType, parentId) {
        const feedback = input.value.trim();
        const existing = state.getCurrentArtifact()?.content;
        try {
            const data = await api.generateArtifact(childType, parentId, feedback, modelSelect.value, pid(), existing);
            const combined = Array.isArray(existing) ? existing.concat(data.result) : data.result;
            state.setCurrentArtifact({ content: combined });
            ui.openRequirementsModal(childType, combined, 
                () => handleSave(childType, parentId),
                () => handleAddMore(childType, parentId),
                () => ui.closeModal()
            );
        } catch (e) {
            ui.showNotification('Ошибка: ' + e.message, 'error');
        }
    }

    generateArtifactBtn.onclick = async () => {
        const pId = parentSelect.value;
        const cType = artifactTypeSelect.value;
        if (!pId || !cType) return;
        
        if (window.utils) window.utils.setLoading(generateArtifactBtn, true);
        try {
            let content;
            const cached = state.getArtifactCache(pId, cType);
            if (cached) {
                content = cached.content;
                state.setCurrentArtifact(cached);
            } else {
                const data = await api.fetchLatestArtifact(pId, cType);
                if (data.exists) {
                    content = data.content;
                    state.setArtifactCache(pId, cType, { id: data.artifact_id, content });
                    state.setCurrentArtifact({ id: data.artifact_id, content });
                } else {
                    const gen = await api.generateArtifact(cType, pId, input.value, modelSelect.value, pid());
                    content = gen.result;
                    state.setCurrentArtifact({ content });
                }
            }
            ui.openRequirementsModal(cType, content, 
                () => handleSave(cType, pId),
                () => handleAddMore(cType, pId),
                () => ui.closeModal()
            );
        } catch (e) {
            ui.showNotification('Ошибка: ' + e.message, 'error');
        } finally {
            if (window.utils) window.utils.setLoading(generateArtifactBtn, false);
        }
    };

    saveArtifactBtn.onclick = async () => {
        const content = input.value.trim();
        if (!content || !pid()) return;
        if (window.utils) window.utils.setLoading(saveArtifactBtn, true);
        try {
            await api.saveArtifact(pid(), artifactTypeSelect.value, content, parentSelect.value);
            ui.showNotification("Сохранено", 'success');
            input.value = "";
            if (window.loadParents) await window.loadParents();
        } catch (e) {
            ui.showNotification(e.message, 'error');
        } finally {
            if (window.utils) window.utils.setLoading(saveArtifactBtn, false);
        }
    };
})();
