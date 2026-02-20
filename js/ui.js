// ui.js - точка входа для UI-функций
console.log('[UI] загрузка начата, window.renderers наличие:', !!window.renderers);

window.ui = {
    renderProjectSelect: window.renderers?.renderProjectSelect,
    renderParentSelect: window.renderers?.renderParentSelect,
    updateGenerateButton: window.renderers?.updateGenerateButton,
    showNotification: window.notifications?.showNotification || function(){},
    openRequirementsModal: window.modals?.openRequirementsModal || function(){},
    closeModal: window.modals?.closeModal || function(){}
};

console.log('[UI] загрузка завершена, window.ui.renderParentSelect тип:', typeof window.ui.renderParentSelect);
