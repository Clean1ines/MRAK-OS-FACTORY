// ui.js - точка входа для UI-функций

window.ui = {
    renderProjectSelect: window.renderers.renderProjectSelect,
    renderParentSelect: window.renderers.renderParentSelect,
    updateGenerateButton: window.renderers.updateGenerateButton,
    showNotification: window.notifications ? window.notifications.showNotification : function(){},
    openRequirementsModal: window.modals ? window.modals.openRequirementsModal : function(){},
    closeModal: window.modals ? window.modals.closeModal : function(){}
};

// ===== ДИАГНОСТИКА =====
console.log('[UI] window.ui перед инициализацией:', window.ui);
console.log('[UI] window.renderers наличие:', !!window.renderers);
console.log('[UI] window.renderers.renderParentSelect наличие:', typeof window.renderers?.renderParentSelect);
