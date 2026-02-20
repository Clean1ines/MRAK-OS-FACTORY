// js/renderers.js - функции отрисовки UI
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
    
    if (currentParentId && latestArtifacts.some(a => a.id === currentParentId)) {
        select.value = currentParentId;
    }
    updateGenerateButton(parentData, select.value, childType);
}

function updateGenerateButton(parentData, selectedId, childType) {
    const parentType = parentData[selectedId];
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
    const data = requirements?.requirements || requirements;
    if (!Array.isArray(data)) {
        container.innerHTML = '<div class="text-red-500">Ошибка данных требований</div>';
        return;
    }
    container.innerHTML = '';
    data.forEach((req, index) => {
        const card = document.createElement('div');
        card.className = "p-4 mb-4 bg-zinc-900 border border-zinc-800 rounded";
        card.innerHTML = `<div><strong>#${index+1}</strong><br>${req.description || ''}</div>`;
        container.appendChild(card);
    });
}

window.renderers = {
    renderProjectSelect,
    renderParentSelect,
    updateGenerateButton,
    renderRequirementsInContainer,
};

// ===== ДИАГНОСТИКА =====
const originalRenderParentSelect = renderParentSelect;
renderParentSelect = function(artifacts, parentData, currentParentId, childType) {
    console.log('[RENDER] renderParentSelect START', { artifactsCount: artifacts.length, childType });
    const allowedTypes = state.getAllowedParentTypes(childType);
    console.log('[RENDER] allowedTypes:', allowedTypes);
    originalRenderParentSelect(artifacts, parentData, currentParentId, childType);
    console.log('[RENDER] renderParentSelect END');
};

const originalUpdateGenerateButton = updateGenerateButton;
updateGenerateButton = function(parentData, selectedId, childType) {
    console.log('[RENDER] updateGenerateButton called', { selectedId, childType });
    console.log('[RENDER] parentType:', parentData[selectedId], 'canGenerate:', state.canGenerate(childType, parentData[selectedId]));
    originalUpdateGenerateButton(parentData, selectedId, childType);
    const btn = document.getElementById('generate-artifact-btn');
    console.log('[RENDER] button display after update:', btn ? btn.style.display : 'btn not found');
};

// Переопределяем в window.renderers
window.renderers.renderParentSelect = renderParentSelect;
window.renderers.updateGenerateButton = updateGenerateButton;

// ===== ДИАГНОСТИКА: ВСЕ ФУНКЦИИ =====
const originalRenderProjectSelect = renderProjectSelect;
renderProjectSelect = function(projects, currentId) {
    console.log('[RENDER] renderProjectSelect START', { projectsCount: projects.length, currentId });
    originalRenderProjectSelect(projects, currentId);
    console.log('[RENDER] renderProjectSelect END');
};

const originalRenderParentSelect = renderParentSelect;
renderParentSelect = function(artifacts, parentData, currentParentId, childType) {
    console.log('[RENDER] renderParentSelect START', { artifactsCount: artifacts.length, childType });
    const allowedTypes = state.getAllowedParentTypes(childType);
    console.log('[RENDER] allowedTypes:', allowedTypes);
    const filtered = artifacts.filter(a => allowedTypes.includes(a.type));
    console.log('[RENDER] filtered count:', filtered.length);
    originalRenderParentSelect(artifacts, parentData, currentParentId, childType);
    console.log('[RENDER] renderParentSelect END');
};

const originalUpdateGenerateButton = updateGenerateButton;
updateGenerateButton = function(parentData, selectedId, childType) {
    console.log('[RENDER] updateGenerateButton START', { selectedId, childType });
    console.log('[RENDER] parentData keys:', Object.keys(parentData));
    console.log('[RENDER] parentType:', parentData[selectedId]);
    console.log('[RENDER] canGenerate:', state.canGenerate(childType, parentData[selectedId]));
    originalUpdateGenerateButton(parentData, selectedId, childType);
    console.log('[RENDER] updateGenerateButton END');
};

const originalRenderRequirementsInContainer = renderRequirementsInContainer;
renderRequirementsInContainer = function(container, requirements) {
    console.log('[RENDER] renderRequirementsInContainer START', { requirementsType: typeof requirements, isArray: Array.isArray(requirements) });
    originalRenderRequirementsInContainer(container, requirements);
    console.log('[RENDER] renderRequirementsInContainer END');
};

const originalRenderReqEngineeringAnalysis = renderReqEngineeringAnalysis;
renderReqEngineeringAnalysis = function(container, analysis) {
    console.log('[RENDER] renderReqEngineeringAnalysis START');
    originalRenderReqEngineeringAnalysis(container, analysis);
    console.log('[RENDER] renderReqEngineeringAnalysis END');
};

// Переопределяем window.renderers
window.renderers = {
    renderProjectSelect,
    renderParentSelect,
    updateGenerateButton,
    renderRequirementsInContainer,
    renderReqEngineeringAnalysis,
};
