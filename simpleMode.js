// simpleMode.js - логика простого режима, прогресс-бара и кнопки "Далее"

let isSimpleMode = false;

function renderProgressBar(currentStage) {
    const container = document.getElementById('progress-bar-container');
    if (!container) return;
    container.classList.remove('hidden');
    const steps = ['idea', 'requirements', 'architecture', 'code', 'tests'];
    const stepElements = document.querySelectorAll('.progress-step');
    stepElements.forEach(el => {
        const step = el.dataset.step;
        el.classList.remove('active', 'completed');
        if (step === currentStage) {
            el.classList.add('active');
        } else if (steps.indexOf(step) < steps.indexOf(currentStage)) {
            el.classList.add('completed');
        }
    });
}

async function updateProgress() {
    const projectId = state.getCurrentProjectId();
    if (!projectId) return;
    try {
        const res = await fetch(`/api/workflow/next?project_id=${encodeURIComponent(projectId)}`);
        const data = await res.json();
        if (!data.error) {
            renderProgressBar(data.next_stage);
        }
    } catch (e) {
        console.error('Failed to update progress', e);
    }
}

async function handleNext() {
    const projectId = state.getCurrentProjectId();
    if (!projectId) {
        ui.showNotification('Сначала выберите проект', 'error');
        return;
    }
    try {
        const res = await fetch(`/api/workflow/next?project_id=${encodeURIComponent(projectId)}`);
        const data = await res.json();
        if (data.error) {
            ui.showNotification(data.error, 'error');
            return;
        }
        if (data.next_stage === 'finished') {
            ui.showNotification('Проект завершён, все этапы пройдены', 'info');
            return;
        }
        if (data.next_stage === 'idea') {
            ui.showNotification('Введите идею в поле ввода и нажмите "Отправить"', 'info');
            return;
        }
        const execRes = await fetch(`/api/workflow/execute_next?project_id=${encodeURIComponent(projectId)}`, {
            method: 'POST'
        });
        const execData = await execRes.json();
        if (execData.error) {
            ui.showNotification(execData.error, 'error');
            return;
        }
        if (execData.existing) {
            ui.showNotification('Этот этап уже пройден. Открываю существующий артефакт.', 'info');
        }
        ui.openRequirementsModal(
            execData.artifact_type,
            execData.content,
            async (updatedContent, validate) => {
                try {
                    const saved = await api.saveArtifactPackage(projectId, execData.parent_id, execData.artifact_type, updatedContent);
                    if (validate) {
                        // FIXED: use api.apiFetch
                        await api.apiFetch('/api/validate_artifact', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ artifact_id: saved.id, status: 'VALIDATED' })
                        });
                        ui.showNotification('Артефакт подтверждён', 'success');
                    } else {
                        ui.showNotification(`Сохранён пакет, ID: ${saved.id}`, 'success');
                    }
                    ui.closeModal();
                    await updateProgress();
                    if (!isSimpleMode && typeof window.loadParents === 'function') {
                        await window.loadParents();
                    }
                } catch (e) {
                    ui.showNotification('Ошибка сохранения: ' + e.message, 'error');
                }
            },
            () => {
                ui.showNotification('Догенерация пока не поддерживается', 'info');
            },
            () => { ui.closeModal(); }
        );
    } catch (e) {
        ui.showNotification('Ошибка: ' + e.message, 'error');
    }
}

function switchMode(mode) {
    isSimpleMode = (mode === 'simple');
    const simpleControls = document.getElementById('simple-controls');
    const advancedControls = document.getElementById('advanced-controls');
    const simpleBtn = document.getElementById('simple-mode-btn');
    const advancedBtn = document.getElementById('advanced-mode-btn');

    if (!simpleControls || !advancedControls || !simpleBtn || !advancedBtn) return;

    if (isSimpleMode) {
        simpleControls.classList.remove('hidden');
        advancedControls.classList.add('hidden');
        simpleBtn.classList.add('bg-cyan-600/30');
        advancedBtn.classList.remove('bg-cyan-600/30');
        document.getElementById('progress-bar-container')?.classList.remove('hidden');
        updateProgress();
    } else {
        simpleControls.classList.add('hidden');
        advancedControls.classList.remove('hidden');
        advancedBtn.classList.add('bg-cyan-600/30');
        simpleBtn.classList.remove('bg-cyan-600/30');
        document.getElementById('progress-bar-container')?.classList.add('hidden');
        if (typeof window.loadParents === 'function') {
            window.loadParents();
        }
    }
    const savedState = JSON.parse(localStorage.getItem('mrak_ui_state') || '{}');
    savedState.isSimple = isSimpleMode;
    localStorage.setItem('mrak_ui_state', JSON.stringify(savedState));
}

function initSimpleMode() {
    const simpleBtn = document.getElementById('simple-mode-btn');
    const advancedBtn = document.getElementById('advanced-mode-btn');
    const nextBtn = document.getElementById('next-btn');

    if (simpleBtn) {
        simpleBtn.addEventListener('click', () => switchMode('simple'));
    }
    if (advancedBtn) {
        advancedBtn.addEventListener('click', () => switchMode('advanced'));
    }
    if (nextBtn) {
        nextBtn.addEventListener('click', handleNext);
    }
    const saved = localStorage.getItem('mrak_ui_state');
    if (saved) {
        const st = JSON.parse(saved);
        if (st.isSimple) {
            switchMode('simple');
        } else {
            switchMode('advanced');
        }
    } else {
        switchMode('advanced');
    }
}

window.simpleMode = {
    init: initSimpleMode,
    switchMode,
    renderProgressBar,
    handleNext,
    updateProgress
};
