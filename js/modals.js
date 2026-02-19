// modals.js - работа с модальными окнами

let currentModal = null;

function closeModal() {
    if (currentModal) {
        currentModal.style.display = 'none';
        document.body.removeChild(currentModal);
        currentModal = null;
    }
}

function openRequirementsModal(artifactType, content, onSave, onAddMore, onCancel) {
    if (currentModal) closeModal();

    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'flex';
    modal.style.position = 'fixed';
    modal.style.top = '0';
    modal.style.left = '0';
    modal.style.width = '100%';
    modal.style.height = '100%';
    modal.style.backgroundColor = 'rgba(0,0,0,0.8)';
    modal.style.zIndex = '1000';
    modal.style.alignItems = 'center';
    modal.style.justifyContent = 'center';
    modal.style.padding = '1rem';

    const modalContent = document.createElement('div');
    modalContent.className = 'modal-content';
    modalContent.style.background = '#111';
    modalContent.style.border = '1px solid #222';
    modalContent.style.borderRadius = '12px';
    modalContent.style.width = '95%';
    modalContent.style.maxWidth = '900px';
    modalContent.style.maxHeight = '90%';
    modalContent.style.overflowY = 'auto';
    modalContent.style.padding = '1.5rem';

    const title = document.createElement('h2');
    title.className = 'text-lg font-bold mb-4';
    title.innerText = artifactType;
    modalContent.appendChild(title);

    const container = document.createElement('div');
    container.id = 'modal-content-container';
    modalContent.appendChild(container);

    const btnDiv = document.createElement('div');
    btnDiv.className = 'flex justify-end gap-3 mt-4 flex-wrap';

    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'px-3 py-1 bg-zinc-700 rounded';
    cancelBtn.innerText = 'Отмена';
    cancelBtn.onclick = () => {
        if (onCancel) onCancel();
        closeModal();
    };
    btnDiv.appendChild(cancelBtn);

    const addMoreBtn = document.createElement('button');
    addMoreBtn.className = 'px-3 py-1 bg-blue-600/20 text-blue-500 rounded';
    addMoreBtn.innerText = 'Добавить ещё';
    addMoreBtn.onclick = () => {
        if (onAddMore) onAddMore();
    };
    btnDiv.appendChild(addMoreBtn);

    const saveBtn = document.createElement('button');
    saveBtn.className = 'px-3 py-1 bg-emerald-600/20 text-emerald-500 rounded';
    saveBtn.innerText = 'Сохранить';
    saveBtn.onclick = () => {
        if (onSave) onSave();
    };
    btnDiv.appendChild(saveBtn);

    modalContent.appendChild(btnDiv);
    modal.appendChild(modalContent);
    document.body.appendChild(modal);
    currentModal = modal;

    // Выбор рендерера в зависимости от типа артефакта
    if (artifactType === 'ReqEngineeringAnalysis') {
        window.renderers.renderReqEngineeringAnalysis(container, content);
    } else {
        window.renderers.renderRequirementsInContainer(container, content);
    }
}

window.modals = {
    closeModal,
    openRequirementsModal,
};

// ===== ДИАГНОСТИКА MODALS =====
console.log('[MODALS] файл загружен, currentModal =', typeof currentModal !== 'undefined' ? currentModal : 'undefined');

const originalCloseModal = window.modals?.closeModal;
if (originalCloseModal) {
    window.modals.closeModal = function() {
        console.log('[MODALS] closeModal called');
        originalCloseModal();
    };
}

const originalOpenRequirementsModal = window.modals?.openRequirementsModal;
if (originalOpenRequirementsModal) {
    window.modals.openRequirementsModal = function(artifactType, content, onSave, onAddMore, onCancel) {
        console.log('[MODALS] openRequirementsModal', { artifactType, contentSummary: typeof content });
        originalOpenRequirementsModal(artifactType, content, onSave, onAddMore, onCancel);
    };
}
