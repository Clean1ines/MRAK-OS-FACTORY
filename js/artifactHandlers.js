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
// ===== ДИАГНОСТИКА ARTIFACTHANDLERS =====
console.log('[ARTIFACTHANDLERS] файл загружен');

(function() {
    const originalHandleSave = window.handleSave; // если есть
    const originalHandleAddMore = window.handleAddMore;
    const originalGenerateClick = document.getElementById('generate-artifact-btn')?.onclick;

    // Если функции не глобальные, они внутри замыкания – нужно переопределить через хуки
    // Просто добавим логи в существующие обработчики, переопределив их

    const saveArtifactBtn = document.getElementById('save-artifact-btn');
    if (saveArtifactBtn) {
        const originalClick = saveArtifactBtn.onclick;
        saveArtifactBtn.onclick = async function(e) {
            console.log('[ARTIFACTHANDLERS] saveArtifactBtn onclick START');
            if (originalClick) await originalClick(e);
            console.log('[ARTIFACTHANDLERS] saveArtifactBtn onclick END');
        };
    }

    const generateArtifactBtn = document.getElementById('generate-artifact-btn');
    if (generateArtifactBtn) {
        const originalClick = generateArtifactBtn.onclick;
        generateArtifactBtn.onclick = async function(e) {
            console.log('[ARTIFACTHANDLERS] generateArtifactBtn onclick START');
            if (originalClick) await originalClick(e);
            console.log('[ARTIFACTHANDLERS] generateArtifactBtn onclick END');
        };
    }
})();
console.log('[ARTIFACTHANDLERS] файл загружен');
const saveBtn = document.getElementById('save-artifact-btn');
if (saveBtn) {
    const originalClick = saveBtn.onclick;
    saveBtn.onclick = async function(e) {
        console.log('[ARTIFACTHANDLERS] saveArtifactBtn onclick START');
        if (originalClick) await originalClick(e);
        console.log('[ARTIFACTHANDLERS] saveArtifactBtn onclick END');
    };
}
const generateBtn = document.getElementById('generate-artifact-btn');
if (generateBtn) {
    const originalClick = generateBtn.onclick;
    generateBtn.onclick = async function(e) {
        console.log('[ARTIFACTHANDLERS] generateArtifactBtn onclick START');
        if (originalClick) await originalClick(e);
        console.log('[ARTIFACTHANDLERS] generateArtifactBtn onclick END');
    };
}
