console.log('ui.js start');
window.ui = {
    renderProjectSelect: window.renderers.renderProjectSelect,
    renderParentSelect: window.renderers.renderParentSelect,
    updateGenerateButton: window.renderers.updateGenerateButton,
    showNotification: window.notifications.showNotification,
    openRequirementsModal: window.modals.openRequirementsModal,
    closeModal: window.modals.closeModal
};
console.log('ui.js end');
