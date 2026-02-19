// main.js - точка входа, инициализация

window.onload = async function() {
    await window.loadModels();   // из projectHandlers
    await window.loadProjects(); // из projectHandlers
    if (state.getCurrentProjectId()) await window.loadParents(); // из projectHandlers
};
