// renderers.js - функции рендеринга элементов интерфейса
console.log('[RENDERERS] загрузка начата');

function renderProjectSelect(projects, currentId) {
    console.log('[RENDERERS] renderProjectSelect', { projectsCount: projects.length, currentId });
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
    console.log('[RENDERERS] renderParentSelect', { artifactsCount: artifacts.length, childType });
    const select = document.getElementById('parent-select');
    if (!select) return;
    const allowedTypes = state.getAllowedParentTypes(childType);
    let filtered = artifacts.filter(a => allowedTypes.includes(a.type));
    console.log('[RENDERERS] filtered count:', filtered.length);
    
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
    console.log('[RENDERERS] updateGenerateButton', { selectedId, childType });
    const parentType = parentData[selectedId];
    console.log('[RENDERERS] parentType:', parentType, 'canGenerate:', state.canGenerate(childType, parentType));
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
    console.log('[RENDERERS] renderRequirementsInContainer', { requirementsType: typeof requirements });
    if (requirements && requirements.requirements && Array.isArray(requirements.requirements)) {
        requirements = requirements.requirements;
    }
    if (!Array.isArray(requirements)) {
        container.innerHTML = '<div class="text-red-500">Ошибка данных</div>';
        return;
    }
    container.innerHTML = '';
    requirements.forEach((req, index) => {
        const card = document.createElement('div');
        card.style.border = '1px solid #333';
        card.style.padding = '1rem';
        card.style.marginBottom = '1rem';
        card.style.background = '#1a1a1c';
        card.innerHTML = `<div><strong>Требование #${index+1}</strong><br>${req.description || ''}</div>`;
        container.appendChild(card);
    });
}

function renderReqEngineeringAnalysis(container, analysis) {
    console.log('[RENDERERS] renderReqEngineeringAnalysis');
    container.innerHTML = '<pre>' + JSON.stringify(analysis, null, 2) + '</pre>';
}

window.renderers = {
    renderProjectSelect,
    renderParentSelect,
    updateGenerateButton,
    renderRequirementsInContainer,
    renderReqEngineeringAnalysis,
};

console.log('[RENDERERS] загрузка завершена, window.renderers определён:', !!window.renderers);
