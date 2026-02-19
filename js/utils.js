// js/utils.js - Общие вспомогательные функции
window.utils = {
    setLoading(btn, isLoading) {
        if (!btn) return;
        if (isLoading) {
            btn.disabled = true;
            btn.dataset.originalText = btn.innerText;
            btn.innerHTML = '<span class="animate-spin mr-2">🌀</span> Обработка...';
        } else {
            btn.disabled = false;
            btn.innerText = btn.dataset.originalText || "Готово";
        }
    },

    formatDate(dateStr) {
        return new Date(dateStr).toLocaleString();
    }
};

// Для обратной совместимости, если где-то вызывается без utils.
window.setLoading = window.utils.setLoading;

// ===== ДИАГНОСТИКА UTILS =====
console.log('[UTILS] файл загружен, window.isSaving =', window.isSaving);

const originalSetLoading = window.setLoading;
window.setLoading = function(button, isLoading) {
    console.log('[UTILS] setLoading', { buttonId: button?.id, isLoading });
    originalSetLoading(button, isLoading);
};

const originalAutoResize = window.autoResize;
window.autoResize = function(textarea) {
    console.log('[UTILS] autoResize', { textareaId: textarea?.id, scrollHeight: textarea?.scrollHeight });
    originalAutoResize(textarea);
};
