// utils.js - общие утилиты
console.log('[UTILS] загрузка начата');

window.isSaving = false;

window.setLoading = function(button, isLoading) {
    console.log('[UTILS] setLoading', { buttonId: button?.id, isLoading });
    if (!button) return;
    if (isLoading) {
        button.disabled = true;
        button.dataset.originalText = button.innerText;
        button.innerHTML = '<span class="spinner"></span> Загрузка...';
    } else {
        button.disabled = false;
        button.innerText = button.dataset.originalText || button.innerText;
    }
};

window.autoResize = function(textarea) {
    console.log('[UTILS] autoResize', { textareaId: textarea?.id });
    if (!textarea) return;
    textarea.style.height = 'auto';
    textarea.style.height = (textarea.scrollHeight) + 'px';
};

console.log('[UTILS] загрузка завершена');
