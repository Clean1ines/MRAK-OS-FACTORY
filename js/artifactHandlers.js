(function() {
    const input = document.getElementById("input");
    const parentSelect = document.getElementById("parent-select");
    const artifactTypeSelect = document.getElementById("artifact-type-select");
    const modelSelect = document.getElementById("model-select");
    const generateArtifactBtn = document.getElementById("generate-artifact-btn");
    const saveArtifactBtn = document.getElementById("save-artifact-btn");
    const pid = () => state.getCurrentProjectId();

    artifactTypeSelect.onchange = async () => { if (window.loadParents) await window.loadParents(); };
    parentSelect.onchange = () => { if (window.renderers) renderers.updateGenerateButton(state.getParentData(), parentSelect.value, artifactTypeSelect.value); };

    generateArtifactBtn.onclick = async () => {
        const model = modelSelect.value;
        if (!model || model.includes("loading")) {
            ui.showNotification("Дождитесь загрузки списка моделей", "warning");
            return;
        }
        const pId = parentSelect.value;
        const cType = artifactTypeSelect.value;
        if (!pId || !cType || !pid()) return;
        
        if (window.utils) window.utils.setLoading(generateArtifactBtn, true);
        try {
            let content;
            const data = await api.fetchLatestArtifact(pId, cType);
            if (data.exists) {
                content = data.content;
            } else {
                const gen = await api.generateArtifact(cType, pId, input.value, model, pid());
                content = gen.result;
            }
            state.setCurrentArtifact({ content });
            ui.openRequirementsModal(cType, content, 
                async () => {
                    const saved = await api.saveArtifactPackage(pid(), pId, cType, state.getCurrentArtifact().content);
                    ui.showNotification("Сохранено", "success");
                    ui.closeModal();
                },
                null, 
                () => ui.closeModal()
            );
        } catch (e) {
            ui.showNotification('Ошибка: ' + e.message, 'error');
        } finally {
            if (window.utils) window.utils.setLoading(generateArtifactBtn, false);
        }
    };
    // ... (остальные функции handleSave и saveArtifactBtn остаются как были в предыдущем шаге)
})();
