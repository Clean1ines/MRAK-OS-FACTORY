// utils.js - общие утилиты

// Флаг для блокировки повторных сохранений (глобальный)
window.isSaving = false;

window.setLoading = function(button, isLoading) {
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

// Автоматическое расширение textarea
window.autoResize = function(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = (textarea.scrollHeight) + 'px';
};
