(function() {
    const input = document.getElementById("input");
    const modelSelect = document.getElementById("model-select");
    const genBtn = document.getElementById("generate-artifact-btn");
    const pSelect = document.getElementById("parent-select");
    const tSelect = document.getElementById("artifact-type-select");

    if (!genBtn) return;

    genBtn.onclick = async () => {
        const model = modelSelect.value;
        const pid = state.getCurrentProjectId();
        const pId = pSelect.value;
        const cType = tSelect.value;

        if (!pid || !pId || model.includes("loading")) {
            alert("Выберите проект, родителя и дождитесь загрузки модели");
            return;
        }

        genBtn.disabled = true;
        genBtn.innerText = "Генерация...";

        try {
            const data = await api.generateArtifact(cType, pId, input.value, model, pid);
            state.setCurrentArtifact({ content: data.result });
            ui.openRequirementsModal(cType, data.result, 
                async () => {
                    await api.saveArtifactPackage(pid, pId, cType, data.result);
                    ui.showNotification("Сохранено!", "success");
                    ui.closeModal();
                },
                null, 
                () => ui.closeModal()
            );
        } catch (e) {
            alert("Ошибка: " + e.message);
        } finally {
            genBtn.disabled = false;
            genBtn.innerText = "Создать/редактировать";
        }
    };
})();
