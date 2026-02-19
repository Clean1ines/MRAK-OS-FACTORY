// js/main.js - Единая точка входа и глобальный перехватчик событий

window.onload = async function() {
    console.log("🚀 MRAK-OS: Запуск системы...");

    // Инициализация моделей и проектов
    try {
        if (window.loadModels) await window.loadModels();
        if (window.loadProjects) await window.loadProjects();
    } catch (e) {
        console.error("Ошибка при начальной загрузке:", e);
    }
};

// Глобальный слушатель кликов. Перехватывает ВСЕ нажатия на кнопки.
document.addEventListener('click', async (e) => {
    // Ищем ближайший элемент, по которому кликнули (поддержка иконок внутри кнопок)
    const target = e.target.closest('button') || e.target;

    // --- 1. КНОПКА ГЕНЕРАЦИИ ---
    if (target.id === 'generate-artifact-btn') {
        e.preventDefault();
        
        const pidSelect = document.getElementById('project-select');
        const modelSelect = document.getElementById('model-select');
        const typeSelect = document.getElementById('artifact-type-select');
        const parentSelect = document.getElementById('parent-select');

        const pid = pidSelect ? pidSelect.value : null;
        const model = modelSelect ? modelSelect.value : 'llama-3.3-70b-versatile';
        const type = typeSelect ? typeSelect.value : null;
        const parentId = parentSelect ? parentSelect.value : null;

        if (!pid) {
            alert("ОШИБКА: Сначала выберите проект!");
            return;
        }

        if (!window.api || typeof window.api.generateArtifact !== 'function') {
            alert("ОШИБКА: API не загружено или недоступно.");
            return;
        }

        const originalText = target.innerText;
        target.disabled = true;
        target.innerText = "Генерация...";

        try {
            console.log(`Отправка запроса: Type=${type}, Parent=${parentId}, Model=${model}, Project=${pid}`);
            const res = await window.api.generateArtifact(type, parentId, "", model, pid);
            console.log("Успешная генерация:", res);
            
            // Открываем модалку, если она есть
            if (window.ui && typeof window.ui.showPreviewModal === 'function') {
                window.ui.showPreviewModal(res);
            } else {
                alert("Артефакт успешно сгенерирован!");
            }
        } catch (err) {
            console.error("Ошибка генерации:", err);
            alert("Ошибка API: " + err.message);
        } finally {
            target.disabled = false;
            target.innerText = originalText;
        }
    }

    // --- 2. КНОПКА ОТПРАВКИ В ЧАТ ---
    if (target.id === 'send-btn') {
        e.preventDefault();
        if (window.handleSendMessage && typeof window.handleSendMessage === 'function') {
            window.handleSendMessage();
        } else {
            console.error("handleSendMessage не найден - проверь chatHandlers.js");
        }
    }

    // --- 3. КНОПКА СОЗДАНИЯ ПРОЕКТА ---
    if (target.id === 'new-project-btn') {
        e.preventDefault();
        if (window.projectHandlers && typeof window.projectHandlers.handleNewProject === 'function') {
            window.projectHandlers.handleNewProject();
        } else {
            alert("Функция создания проекта пока не подключена.");
        }
    }

    // --- 4. КНОПКА СОХРАНЕНИЯ АРТЕФАКТА ---
    if (target.id === 'save-artifact-btn') {
        e.preventDefault();
        if (window.artifactHandlers && typeof window.artifactHandlers.handleSaveArtifact === 'function') {
            window.artifactHandlers.handleSaveArtifact();
        } else {
            alert("Функция сохранения артефакта пока не подключена.");
        }
    }
    
    // --- 5. КНОПКА ОБНОВЛЕНИЯ РОДИТЕЛЕЙ ---
    if (target.id === 'refresh-parents') {
        e.preventDefault();
        const pidSelect = document.getElementById('project-select');
        if (pidSelect && pidSelect.value && window.loadArtifacts) {
            window.loadArtifacts(pidSelect.value);
        } else {
            alert("Выберите проект для обновления связей.");
        }
    }
});

// Слушатель изменения селектов (чтобы кнопка перерисовывалась при смене типа артефакта)
document.addEventListener('change', (e) => {
    const target = e.target;
    
    if (target.id === 'artifact-type-select' || target.id === 'parent-select') {
        if (window.state && window.renderers && typeof window.renderers.updateGenerateButton === 'function') {
            const typeSelect = document.getElementById('artifact-type-select');
            const parentSelect = document.getElementById('parent-select');
            
            if (typeSelect && parentSelect) {
                window.renderers.updateGenerateButton(
                    window.state.getParentData ? window.state.getParentData() : {}, 
                    parentSelect.value, 
                    typeSelect.value
                );
            }
        }
    }
});