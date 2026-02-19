// ui.js - точка входа для UI-функций, собирает все модули

// Импортируем функции из других модулей через window (они уже должны быть загружены)
// Но мы просто переназначаем для удобства

window.ui = {
    // renderers
    renderProjectSelect: window.renderers.renderProjectSelect,
    renderParentSelect: window.renderers.renderParentSelect,
    updateGenerateButton: window.renderers.updateGenerateButton,
    // notifications
    showNotification: window.notifications.showNotification,
    // modals
    openRequirementsModal: window.modals.openRequirementsModal,
    closeModal: window.modals.closeModal,
};
