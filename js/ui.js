// ui.js - точка входа для UI-функций

window.ui = {
    renderProjectSelect: window.renderers.renderProjectSelect,
    renderParentSelect: window.renderers.renderParentSelect,
    updateGenerateButton: window.renderers.updateGenerateButton,
    showNotification: window.notifications ? window.notifications.showNotification : function(){},
    openRequirementsModal: window.modals ? window.modals.openRequirementsModal : function(){},
    closeModal: window.modals ? window.modals.closeModal : function(){}
};
