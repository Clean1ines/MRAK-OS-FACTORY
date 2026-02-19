window.onload = async function() {
    console.log("MRAK-OS Frontend Initialization...");
    try {
        // 1. Сначала модели (уже починили в прошлом шаге)
        if (window.loadModels) await window.loadModels();
        // 2. Потом проекты
        if (window.loadProjects) await window.loadProjects();
        
        // 3. ПРИНУДИТЕЛЬНО вешаем клик на кнопку генерации (подстраховка)
        const genBtn = document.getElementById('generate-artifact-btn');
        if (genBtn) {
            genBtn.onclick = window.handleGenerateArtifact;
            console.log("✅ Generate button listener attached");
        }
    } catch (e) {
        console.error("Init failed:", e);
    }
};
