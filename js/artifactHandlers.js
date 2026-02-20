// artifactHandlers.js - работа с артефактами (сохранение, генерация)
console.log('[ARTIFACTHANDLERS] загрузка начата');

const saveArtifactBtn = document.getElementById('save-artifact-btn');
const generateArtifactBtn = document.getElementById('generate-artifact-btn');
const input = document.getElementById('input');
const parentSelect = document.getElementById('parent-select');
const artifactTypeSelect = document.getElementById('artifact-type-select');
const generateCheckbox = document.getElementById('generate-checkbox');
const modelSelect = document.getElementById('model-select');

if (saveArtifactBtn) {
    saveArtifactBtn.onclick = async function(e) {
        console.log('[ARTIFACTHANDLERS] saveArtifactBtn click');
        const content = input.value.trim();
        if (!content) {
            window.ui?.showNotification('Введите содержимое', 'error');
            return;
        }
        const pid = state.getCurrentProjectId();
        if (!pid) {
            window.ui?.showNotification('Сначала выберите проект', 'error');
            return;
        }
        const artifactType = artifactTypeSelect.value;
        const parentId = parentSelect.value || null;
        const generate = generateCheckbox.checked;
        const model = modelSelect.value;

        try {
            const data = await api.saveArtifact(pid, artifactType, content, parentId, generate, model);
            window.ui?.showNotification(`Артефакт сохранён, ID: ${data.id}`, 'success');
            input.value = '';
            input.style.height = '44px';
            await window.loadParents?.();
        } catch (e) {
            window.ui?.showNotification('Ошибка сохранения: ' + e.message, 'error');
        }
    };
}

if (generateArtifactBtn) {
    generateArtifactBtn.onclick = async function(e) {
        console.log('[ARTIFACTHANDLERS] generateArtifactBtn click');
        // Здесь должна быть логика генерации, но пока оставим просто заглушку
        window.ui?.showNotification('Генерация пока не реализована', 'info');
    };
}

console.log('[ARTIFACTHANDLERS] загрузка завершена');
