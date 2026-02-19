// renderers.js - функции рендеринга элементов интерфейса

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
    if (currentParentId && parentData[currentParentId] && allowedTypes.includes(parentData[currentParentId])) {
        const exists = latestArtifacts.some(a => a.id === currentParentId);
        if (exists) select.value = currentParentId;
    }
    updateGenerateButton(parentData, select.value, childType);
}

function updateGenerateButton(parentData, selectedId, childType) {
    console.log("updateGenerateButton called with:", { parentData, selectedId, childType });
    const parentType = parentData[selectedId];
    console.log("parentType:", parentType, "canGenerate:", state.canGenerate(childType, parentType));
    const btn = document.getElementById('generate-artifact-btn');
    if (!btn) return;
    if (parentType && state.canGenerate(childType, parentType)) {
        btn.style.display = 'inline-block';
        btn.innerText = `Создать/редактировать ${childType}`;
    } else {
        btn.style.display = 'none';
    }
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
                    window.autoResize(textarea);
                    if (f.field === 'acceptance_criteria') {
                        req[f.field] = e.target.value.split('\n').filter(line => line.trim() !== '');
                    } else {
                        req[f.field] = e.target.value;
                    }
                };
                textarea.addEventListener('input', () => window.autoResize(textarea));
                setTimeout(() => window.autoResize(textarea), 0);
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
                    window.autoResize(textarea);
                };
                textarea.addEventListener('input', () => window.autoResize(textarea));
                setTimeout(() => window.autoResize(textarea), 0);
                div.appendChild(textarea);
            }
            containerEl.appendChild(div);
        }
    };
    
    renderObject(analysis, container);
}

window.renderers = {
    renderProjectSelect,
    renderParentSelect,
    updateGenerateButton,
    renderRequirementsInContainer,
    renderReqEngineeringAnalysis,
};
