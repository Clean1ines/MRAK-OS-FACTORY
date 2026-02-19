// ui.js - функции для обновления интерфейса

function renderProjectSelect(projects, currentId) {
    const select = document.getElementById('project-select');
    if (!select) return;
    select.innerHTML = '<option value="">-- Выберите проект --</option>';
    projects.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.innerText = p.name;
        if (p.id === currentId) opt.selected = true;
        select.appendChild(opt);
    });
}

function renderParentSelect(artifacts, parentData) {
    const select = document.getElementById('parent-select');
    if (!select) return;
    select.innerHTML = '<option value="">-- нет --</option>';
    artifacts.forEach(a => {
        const opt = document.createElement('option');
        opt.value = a.id;
        opt.innerText = `${a.type} (${a.created_at}) : ${a.summary || ''}`;
        select.appendChild(opt);
    });
    // обновляем кнопку генерации
    const selectedId = select.value;
    updateGenerateBrButton(parentData, selectedId);
}

function updateGenerateBrButton(parentData, selectedId) {
    const btn = document.getElementById('generate-br-btn');
    if (!btn) return;
    const selectedType = parentData[selectedId];
    if (selectedType === 'ProductCouncilAnalysis') {
        btn.style.display = 'inline-block';
    } else {
        btn.style.display = 'none';
    }
}

// Уведомления
function showNotification(message, type = 'info') {
    // Создаём контейнер, если нет
    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = '1000';
        document.body.appendChild(container);
    }
    const notification = document.createElement('div');
    notification.innerText = message;
    notification.style.background = type === 'error' ? '#f56565' : '#48bb78';
    notification.style.color = 'white';
    notification.style.padding = '10px 20px';
    notification.style.marginBottom = '10px';
    notification.style.borderRadius = '5px';
    notification.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
    container.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}

// Модальное окно требований
let currentModal = null;

function closeModal() {
    if (currentModal) {
        currentModal.style.display = 'none';
        document.body.removeChild(currentModal);
        currentModal = null;
    }
}

function openRequirementsModal(requirements, onSave, onRegenerate, onCancel) {
    // Закрываем предыдущее, если есть
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

    const content = document.createElement('div');
    content.className = 'modal-content';
    content.style.background = '#111';
    content.style.border = '1px solid #222';
    content.style.borderRadius = '12px';
    content.style.width = '80%';
    content.style.maxWidth = '800px';
    content.style.maxHeight = '80%';
    content.style.overflowY = 'auto';
    content.style.padding = '1.5rem';

    const title = document.createElement('h2');
    title.className = 'text-lg font-bold mb-4';
    title.innerText = 'Сгенерированные бизнес-требования';
    content.appendChild(title);

    const reqContainer = document.createElement('div');
    reqContainer.id = 'requirements-container';
    content.appendChild(reqContainer);

    // Кнопки
    const btnDiv = document.createElement('div');
    btnDiv.className = 'flex justify-end gap-3 mt-4';

    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'px-3 py-1 bg-zinc-700 rounded';
    cancelBtn.innerText = 'Отмена';
    cancelBtn.onclick = () => {
        if (onCancel) onCancel();
        closeModal();
    };
    btnDiv.appendChild(cancelBtn);

    const regenerateBtn = document.createElement('button');
    regenerateBtn.className = 'px-3 py-1 bg-blue-600/20 text-blue-500 rounded';
    regenerateBtn.innerText = 'Перегенерировать';
    regenerateBtn.onclick = () => {
        if (onRegenerate) onRegenerate();
    };
    btnDiv.appendChild(regenerateBtn);

    const saveBtn = document.createElement('button');
    saveBtn.className = 'px-3 py-1 bg-emerald-600/20 text-emerald-500 rounded';
    saveBtn.innerText = 'Сохранить все';
    saveBtn.onclick = () => {
        if (onSave) onSave();
    };
    btnDiv.appendChild(saveBtn);

    content.appendChild(btnDiv);
    modal.appendChild(content);
    document.body.appendChild(modal);
    currentModal = modal;

    // Рендерим требования
    renderRequirementsInContainer(reqContainer, requirements);
}

function renderRequirementsInContainer(container, requirements) {
    container.innerHTML = '';
    requirements.forEach((req, index) => {
        const card = document.createElement('div');
        card.className = 'requirement-card';
        card.style.border = '1px solid #333';
        card.style.borderRadius = '8px';
        card.style.padding = '1rem';
        card.style.marginBottom = '1rem';
        card.style.background = '#1a1a1c';

        const header = document.createElement('div');
        header.className = 'flex justify-between items-center mb-2';
        const title = document.createElement('span');
        title.className = 'text-sm font-bold';
        title.innerText = `Требование #${index+1}`;
        header.appendChild(title);
        const delBtn = document.createElement('button');
        delBtn.className = 'text-red-500 text-xs';
        delBtn.innerText = 'Удалить';
        delBtn.onclick = () => {
            requirements.splice(index, 1);
            renderRequirementsInContainer(container, requirements);
        };
        header.appendChild(delBtn);
        card.appendChild(header);

        // Поля
        const fields = [
            { label: 'Описание', field: 'description', type: 'input' },
            { label: 'Приоритет', field: 'priority', type: 'input' },
            { label: 'Заинтересованная сторона', field: 'stakeholder', type: 'input' },
            { label: 'Критерии приемки (каждый с новой строки)', field: 'acceptance_criteria', type: 'textarea' },
            { label: 'Бизнес-ценность', field: 'business_value', type: 'textarea' },
        ];

        fields.forEach(f => {
            const label = document.createElement('div');
            label.className = 'text-xs text-zinc-400 mt-2';
            label.innerText = f.label;
            card.appendChild(label);

            if (f.type === 'input') {
                const input = document.createElement('input');
                input.type = 'text';
                input.className = 'w-full bg-zinc-800 text-white border border-zinc-700 rounded px-2 py-1';
                input.value = req[f.field] || '';
                input.oninput = (e) => { req[f.field] = e.target.value; };
                card.appendChild(input);
            } else {
                const textarea = document.createElement('textarea');
                textarea.className = 'w-full bg-zinc-800 text-white border border-zinc-700 rounded px-2 py-1';
                textarea.rows = 3;
                let value = req[f.field];
                if (Array.isArray(value)) value = value.join('\n');
                textarea.value = value || '';
                textarea.oninput = (e) => {
                    if (f.field === 'acceptance_criteria') {
                        req[f.field] = e.target.value.split('\n').filter(line => line.trim() !== '');
                    } else {
                        req[f.field] = e.target.value;
                    }
                };
                card.appendChild(textarea);
            }
        });

        container.appendChild(card);
    });
}

// Экспортируем в глобальную область
window.ui = {
    renderProjectSelect,
    renderParentSelect,
    updateGenerateBrButton,
    showNotification,
    openRequirementsModal,
    closeModal,
};
