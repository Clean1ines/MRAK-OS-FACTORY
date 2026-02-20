// main.js - инициализация
console.log('[MAIN] загрузка начата');

window.onload = async function() {
    console.log('[MAIN] onload start');
    try {
        await window.loadModels?.();
        await window.loadProjects?.();
        if (state.getCurrentProjectId()) await window.loadParents?.();
    } catch (e) {
        console.error('[MAIN] onload error:', e);
    }
    console.log('[MAIN] onload end');
};

console.log('[MAIN] загрузка завершена');
