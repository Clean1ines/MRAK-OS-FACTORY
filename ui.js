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

function renderParentSelect(artifacts, parentData, currentParentId, childType) {
    const select = document.getElementById('parent-select');
    if (!select) return;
    const allowedTypes = state.getAllowedParentTypes(childType);
    let filtered = artifacts.filter(a => allowedTypes.includes(a.type));
    const latestByType = {};
    filtered.forEach(a => {
        const type = a.type;
        const verNum = parseInt(a.version) || 0;
        if (!latestByType[type] || verNum > (parseInt(latestByType[type].version) || 0)) {
            latestByType[type] = a;
        }
    });
    const latestArtifacts = Object.values(latestByType);

    select.innerHTML = '<option value="">-- нет --</option>';
    latestArtifacts.forEach(a => {
        const opt = document.createElement('option');
        opt.value = a.id;
        opt.innerText = `${a.type} (v${a.version}) : ${a.summary || ''}`;
        select.appendChild(opt);
    });
    // Если сохранённый parentId подходит под новый тип, выбираем его
    if (currentParentId && parentData[currentParentId] && allowedTypes.includes(parentData[currentParentId])) {
        const exists = latestArtifacts.some(a => a.id === currentParentId);
        if (exists) select.value = currentParentId;
    }
    updateGenerateButton(parentData, select.value, childType);
}

function updateGenerateButton(parentData, selectedId, childType) {
    const btn = document.getElementById('generate-artifact-btn');
    if (!btn) return;
    const parentType = parentData[selectedId];
    if (parentType && state.canGenerate(childType, parentType)) {
        btn.style.display = 'inline-block';
        btn.innerText = `Создать/редактировать ${childType}`;
    } else {
        btn.style.display = 'none';
    }
}

// Стилизованное уведомление
function showNotification(message, type = 'info') {
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
    notification.style.background = type === 'error' ? '#f56565' : '#0f172a';
    notification.style.color = type === 'error' ? 'white' : '#0ff';
    notification.style.border = type === 'error' ? '1px solid #f56565' : '1px solid #0ff';
    notification.style.boxShadow = type === 'error' ? '0 0 10px #f56565' : '0 0 10px #0ff';
    notification.style.padding = '10px 20px';
    notification.style.marginBottom = '10px';
    notification.style.borderRadius = '5px';
    notification.style.fontFamily = "'JetBrains Mono', monospace";
    container.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}

let currentModal = null;

function closeModal() {
    if (currentModal) {
        currentModal.style.display = 'none';
        document.body.removeChild(currentModal);
        currentModal = null;
    }
}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = (textarea.scrollHeight) + 'px';
}

function renderRequirementsInContainer(container, requirements) {
    console.log('renderRequirementsInContainer called with:', requirements);
    if (requirements && requirements.requirements && Array.isArray(requirements.requirements)) {
        requirements = requirements.requirements;
    }
    if (!Array.isArray(requirements)) {
        console.error('requirements is not an array:', requirements);
        container.innerHTML = '<div class="text-red-500">Ошибка: данные не являются массивом требований</div>';
        return;
    }
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

        const fields = [
            { label: 'Описание', field: 'description', type: 'textarea' },
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
                input.className = 'w-full bg-zinc-800 text-white border border-zinc-700 rounded px-2 py-1 text-base';
                input.value = req[f.field] || '';
                input.oninput = (e) => { req[f.field] = e.target.value; };
                card.appendChild(input);
            } else {
                const textarea = document.createElement('textarea');
                textarea.className = 'w-full bg-zinc-800 text-white border border-zinc-700 rounded px-2 py-1 text-base';
                textarea.rows = 2;
                textarea.style.resize = 'none';
                let value = req[f.field];
                if (Array.isArray(value)) value = value.join('\n');
                textarea.value = value || '';
                textarea.oninput = (e) => {
                    autoResize(textarea);
                    if (f.field === 'acceptance_criteria') {
                        req[f.field] = e.target.value.split('\n').filter(line => line.trim() !== '');
                    } else {
                        req[f.field] = e.target.value;
                    }
                };
                textarea.addEventListener('input', () => autoResize(textarea));
                setTimeout(() => autoResize(textarea), 0);
                card.appendChild(textarea);
            }
        });

        container.appendChild(card);
    });
}

function renderReqEngineeringAnalysis(container, analysis) {
    console.log('renderReqEngineeringAnalysis called with:', analysis);
    container.innerHTML = '';
    
    if (analysis && analysis.content && typeof analysis.content === 'object') {
        analysis = analysis.content;
    }
    if (!analysis || typeof analysis !== 'object') {
        container.innerHTML = '<div class="text-red-500">Ошибка: анализ не является объектом</div>';
        return;
    }
    if (Object.keys(analysis).length === 0) {
        container.innerText = 'Анализ пуст';
        return;
    }

    const renderObject = (obj, containerEl) => {
        for (const [key, value] of Object.entries(obj)) {
            const div = document.createElement('div');
            div.className = 'mb-2';
            
            const label = document.createElement('div');
            label.className = 'text-xs text-zinc-400 font-bold';
            label.innerText = key;
            div.appendChild(label);
            
            if (value && typeof value === 'object' && !Array.isArray(value)) {
                const nestedDiv = document.createElement('div');
                nestedDiv.className = 'ml-4 border-l border-zinc-700 pl-2';
                renderObject(value, nestedDiv);
                div.appendChild(nestedDiv);
            } else if (Array.isArray(value)) {
                value.forEach((item, idx) => {
                    const itemDiv = document.createElement('div');
                    itemDiv.className = 'flex items-center gap-2 mb-1';
                    const input = document.createElement('input');
                    input.type = 'text';
                    input.className = 'w-full bg-zinc-800 text-white border border-zinc-700 rounded px-2 py-1 text-base';
                    input.value = item || '';
                    input.oninput = (e) => { value[idx] = e.target.value; };
                    itemDiv.appendChild(input);
                    const delBtn = document.createElement('button');
                    delBtn.className = 'text-red-500 text-xs';
                    delBtn.innerText = '✕';
                    delBtn.onclick = () => {
                        value.splice(idx, 1);
                        renderReqEngineeringAnalysis(container, analysis);
                    };
                    itemDiv.appendChild(delBtn);
                    div.appendChild(itemDiv);
                });
                const addBtn = document.createElement('button');
                addBtn.className = 'text-xs bg-emerald-600/20 text-emerald-500 px-2 py-1 rounded mt-1';
                addBtn.innerText = '+ Добавить элемент';
                addBtn.onclick = () => {
                    value.push('');
                    renderReqEngineeringAnalysis(container, analysis);
                };
                div.appendChild(addBtn);
            } else {
                const textarea = document.createElement('textarea');
                textarea.className = 'w-full bg-zinc-800 text-white border border-zinc-700 rounded px-2 py-1 text-base';
                textarea.rows = 2;
                textarea.style.resize = 'none';
                textarea.value = value || '';
                textarea.oninput = (e) => { 
                    obj[key] = e.target.value;
                    autoResize(textarea);
                };
                textarea.addEventListener('input', () => autoResize(textarea));
                setTimeout(() => autoResize(textarea), 0);
                div.appendChild(textarea);
            }
            containerEl.appendChild(div);
        }
    };
    
    renderObject(analysis, container);
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
    modalContent.style.border = '1px solid #0ff';
    modalContent.style.borderRadius = '12px';
    modalContent.style.width = '95%';
    modalContent.style.maxWidth = '900px';
    modalContent.style.maxHeight = '90%';
    modalContent.style.overflowY = 'auto';
    modalContent.style.padding = '1.5rem';
    modalContent.style.boxShadow = '0 0 20px #0ff';

    const title = document.createElement('h2');
    title.className = 'text-lg font-bold mb-4';
    title.style.color = '#0ff';
    title.innerText = artifactType;
    modalContent.appendChild(title);

    const container = document.createElement('div');
    container.id = 'modal-content-container';
    modalContent.appendChild(container);

    // Отслеживаем изменения
    let contentChanged = false;
    const markChanged = () => { contentChanged = true; saveBtn.disabled = false; };

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

    // Кнопка "Подтвердить" (валидация)
    const validateBtn = document.createElement('button');
    validateBtn.className = 'px-3 py-1 bg-green-600/20 text-green-500 rounded';
    validateBtn.innerText = 'Подтвердить';
    validateBtn.onclick = () => {
        // Собираем текущее содержимое
        const updatedContent = gatherContent();
        if (onSave) onSave(updatedContent, true);
    };
    btnDiv.appendChild(validateBtn);

    // Кнопка "Сохранить" (без валидации)
    const saveBtn = document.createElement('button');
    saveBtn.className = 'px-3 py-1 bg-emerald-600/20 text-emerald-500 rounded';
    saveBtn.innerText = 'Сохранить';
    saveBtn.disabled = true; // по умолчанию неактивна
    saveBtn.onclick = () => {
        const updatedContent = gatherContent();
        if (onSave) onSave(updatedContent, false);
    };
    btnDiv.appendChild(saveBtn);

    modalContent.appendChild(btnDiv);
    modal.appendChild(modalContent);
    document.body.appendChild(modal);
    currentModal = modal;

    // Функция сбора текущего содержимого
    function gatherContent() {
        if (artifactType === 'ReqEngineeringAnalysis') {
            // нужно собрать из DOM
            // упрощённо: возвращаем то, что в state (но оно уже должно обновляться через oninput)
            // для полноты можно реализовать парсинг, но пока так
            return content; // заглушка
        } else {
            // для массива требований
            return content; // заглушка
        }
    }

    // Рендерим контент и добавляем слушатели изменений
    if (artifactType === 'ReqEngineeringAnalysis') {
        renderReqEngineeringAnalysis(container, content);
        // Добавляем слушатели для отслеживания изменений
        container.querySelectorAll('input, textarea').forEach(el => {
            el.addEventListener('input', markChanged);
        });
    } else {
        renderRequirementsInContainer(container, content);
        container.querySelectorAll('input, textarea').forEach(el => {
            el.addEventListener('input', markChanged);
        });
    }
}

// ADDED: отображение истории уточнения в области сообщений
function renderClarificationHistory(history) {
    const messagesDiv = document.getElementById('messages');
    messagesDiv.innerHTML = '';
    history.forEach(msg => {
        const div = document.createElement('div');
        if (msg.role === 'user') {
            div.className = 'border-l-2 border-zinc-800 pl-6 text-sm text-zinc-400';
            div.innerText = msg.content;
        } else {
            div.className = 'markdown-body';
            div.innerHTML = marked.parse(msg.content);
        }
        messagesDiv.appendChild(div);
    });
    const placeholder = document.getElementById('messages-placeholder');
    if (placeholder) placeholder.style.display = 'none';
    document.getElementById('scroll-anchor')?.scrollIntoView({ behavior: 'smooth' });
}

// Функция для рендера прогресс-бара (вызывается из simpleMode)
function renderProgressBar(stage) {
    const steps = ['idea', 'requirements', 'architecture', 'code', 'tests'];
    const stepElements = document.querySelectorAll('.progress-step');
    if (!stepElements.length) return;
    stepElements.forEach(el => {
        const step = el.dataset.step;
        el.classList.remove('active', 'completed');
        if (step === stage) {
            el.classList.add('active');
        } else if (steps.indexOf(step) < steps.indexOf(stage)) {
            el.classList.add('completed');
        }
    });
}

window.ui = {
    renderProjectSelect,
    renderParentSelect,
    updateGenerateButton,
    showNotification,
    openRequirementsModal,
    closeModal,
    renderProgressBar,
    // ADDED
    renderClarificationHistory
};
