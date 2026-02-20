// js/main.js
window.onload = async function() {
    console.log("🚀 MRAK-OS: SYSTEM_STARTUP");

    try {
        // Грузим базовые данные
        if (window.api && window.api.fetchModels) {
            const models = await window.api.fetchModels();
            // Тут должен быть твой рендерер моделей, если его нет - просто лог
            console.log("Models loaded:", models);
        }
        
        if (window.api && window.api.fetchProjects) {
            const projects = await window.api.fetchProjects();
            if (window.renderers && window.renderers.renderProjectSelect) {
                window.renderers.renderProjectSelect(projects, null);
            }
        }
    } catch (e) {
        console.error("Startup error:", e);
    }
};
// ===== ДИАГНОСТИКА =====
console.log('[MAIN] страница загружена, запуск onload');
console.log('[MAIN] window.state:', !!window.state);
console.log('[MAIN] window.renderers:', !!window.renderers);
console.log('[MAIN] window.ui:', !!window.ui);
console.log('[MAIN] window.api:', !!window.api);
console.log('[MAIN] onload будет вызван');
window.onload = async function() {
    console.log('[MAIN] onload start');
    await window.loadModels();
    await window.loadProjects();
    if (state.getCurrentProjectId()) await window.loadParents();
    console.log('[MAIN] onload end');
};
