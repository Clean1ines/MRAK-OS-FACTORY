// artifactHandlers.js - работа с артефактами
console.log('[ARTIFACTHANDLERS] загрузка начата');

(function() {
    const saveBtn = document.getElementById('save-artifact-btn');
    const generateBtn = document.getElementById('generate-artifact-btn');

    if (saveBtn) {
        const originalClick = saveBtn.onclick;
        saveBtn.onclick = async function(e) {
            console.log('[ARTIFACTHANDLERS] saveArtifactBtn onclick');
            if (originalClick) await originalClick(e);
        };
    }

    if (generateBtn) {
        const originalClick = generateBtn.onclick;
        generateBtn.onclick = async function(e) {
            console.log('[ARTIFACTHANDLERS] generateArtifactBtn onclick');
            if (originalClick) await originalClick(e);
        };
    }

    console.log('[ARTIFACTHANDLERS] загрузка завершена');
})();
