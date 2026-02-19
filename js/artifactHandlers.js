(function() {
    // Функция, которую вызывает кнопка "Создать"
    window.handleGenerateArtifact = async function() {
        const btn = document.getElementById('generate-artifact-btn');
        
        // Важно: проверяем, что state реально существует
        if (!window.state) {
            console.error("Критическая ошибка: объект state не найден!");
            return;
        }

        const pid = window.state.getCurrentProjectId ? window.state.getCurrentProjectId() : document.getElementById('project-select')?.value;
        const model = window.state.getCurrentModel ? window.state.getCurrentModel() : document.getElementById('model-select')?.value;
        const parentId = document.getElementById('parent-select')?.value;
        const type = document.getElementById('artifact-type-select')?.value;

        if (!pid) {
            alert("Сначала выбери проект, блядь!");
            return;
        }

        try {
            if (btn) {
                btn.disabled = true;
                btn.dataset.oldText = btn.innerText;
                btn.innerText = "ЕБАШУ...";
            }
            
            console.log(`Generating ${type} for project ${pid} using ${model}...`);
            
            const result = await window.api.generateArtifact(type, parentId, "", model, pid);
            
            // Если это бизнес-требования, открываем модалку
            if (window.ui && window.ui.showPreviewModal) {
                window.ui.showPreviewModal(result);
            } else {
                console.log("Result received:", result);
                alert("Готово! Смотри консоль или модалку.");
            }
        } catch (e) {
            console.error("Generation failed:", e);
            alert("Ошибка при генерации: " + e.message);
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerText = btn.dataset.oldText || "Создать/редактировать";
            }
        }
    };

    // Привязываем к физической кнопке
    const bindBtn = () => {
        const btn = document.getElementById('generate-artifact-btn');
        if (btn) {
            btn.onclick = window.handleGenerateArtifact;
            console.log(">>> Обработчик генерации привязан к кнопке");
        }
    };

    // Пытаемся привязать сразу и на всякий случай через секунду (если DOM тормозит)
    bindBtn();
    setTimeout(bindBtn, 1000);
})();