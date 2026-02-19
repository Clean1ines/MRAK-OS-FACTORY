(function() {
    // Функция, которую вызывает кнопка "Создать"
    window.handleGenerateArtifact = async function() {
        const btn = document.getElementById('generate-artifact-btn');
        const pid = state.getCurrentProjectId();
        const model = state.getCurrentModel();
        const parentId = state.getCurrentParentId();
        const type = state.getArtifactType();

        if (!pid) {
            alert("Сначала выбери проект, блядь!");
            return;
        }

        try {
            if (btn) btn.disabled = true;
            console.log(`Generating ${type} for project ${pid} using ${model}...`);
            
            const result = await api.generateArtifact(type, parentId, "", model, pid);
            
            // Если это бизнес-требования, открываем модалку (как в твоем синтезе Титанов)
            if (type === 'BusinessRequirementPackage' && window.ui && ui.showPreviewModal) {
                ui.showPreviewModal(result);
            } else {
                alert("Готово! Проверь список артефактов.");
            }
        } catch (e) {
            console.error("Generation failed:", e);
            alert("Ошибка при генерации: " + e.message);
        } finally {
            if (btn) btn.disabled = false;
        }
    };
    
    // Привязываем к физической кнопке, если она уже в DOM
    const btn = document.getElementById('generate-artifact-btn');
    if (btn) {
        btn.onclick = window.handleGenerateArtifact;
    }
})();
