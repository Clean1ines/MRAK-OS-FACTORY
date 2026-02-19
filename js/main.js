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